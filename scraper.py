import sys
import json
import logging

from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException

from time import sleep

logging.basicConfig(filename='scraper.log', 
	level=logging.DEBUG, 
	format='%(asctime)s %(message)s', 
	datefmt='%m/%d/%Y %I:%M:%S %p')

def parse_args():
	logging.info("Parsing Arguments")
	args = sys.argv
	if len(sys.argv) < 3:
		raise AttributeError("No arguments were provided, you must provide the starting URL for a category to scrape, and the category")
		
	return sys.argv

def parse_adfly(browser, link):
	browser.get(link)
	WebDriverWait(browser, timeout).until(EC.visibility_of_element_located((By.XPATH, "//a[@class='mwButton']")))
	link = browser.find_element_by_class_name('mwButton').get_attribute('href')
	logging.info("Actual Link: " + link)
	return link
		
	
def parse_post_page(browser, link, data):
	try:
		browser.execute_script("$(window.open('" + link + "'))")
		browser.switch_to_window(browser.window_handles[1])
		WebDriverWait(browser, timeout).until(EC.visibility_of_element_located((By.XPATH, "//a[@id='logo']")))

		# Build data for json
		item={}
		item_name = browser.find_element_by_class_name('entry-title').text
		item['link'] = link
		item['image_link'] = browser.find_element_by_class_name('the_content_wrapper').find_element_by_xpath('//img[contains(@class, "size-full")]').get_attribute('src')
		item['section'] = browser.find_element_by_xpath('//meta[contains(@property, "article:section")]').get_attribute('content')
		
		try:
			google_link=browser.find_element_by_link_text('GOOGLE DRIVE').get_attribute('href')
			#print("google link: " + google_link)
			actual_link = parse_adfly(browser, google_link)
		except NoSuchElementException:
			mega_link=browser.find_element_by_link_text('MEGA').get_attribute('href')
			#print("mega link: " + mega_link)
			actual_link = parse_adfly(browser, mega_link)
		#except Exception as e:
			#print("Still having an issue with this link: " + link)
			#raise e

		item['download_link'] = actual_link
		data[item_name] = item
		return data
		
	finally:
		browser.close()
		browser.switch_to_window(browser.window_handles[0])
	
	
def parse_landing_page(browser, data):
	post_items=browser.find_elements_by_xpath("//div[contains(@class, 'post-item')]")
	#print(post_items)
	for post in post_items:
		item_name = post.find_element_by_class_name('entry-title').text
		if item_name not in data:
			image_wrapper=post.find_element_by_class_name('image_wrapper')
			image_url=image_wrapper.find_element_by_tag_name('img').get_attribute('src')
			link=image_wrapper.find_element_by_tag_name('a').get_attribute('href')
			parse_post_page(browser, link, data)
		else:
			logging.warning("Item: '" + item_name + "' is already in the data collection, so we'll skip it.")
			
	return data
	
args = parse_args()

start_url = args[1]
category = args[2]

data = {}

logging.info("Start URL: " + start_url)
logging.info("Scraping Category: " + category)

try:
	with open('data.json') as f:
		data = json.load(f)
except IOError:
	logging.warning("Couldn't file the file, we'll make a new one.")


logging.debug(json.dumps(data, indent=4, sort_keys=True))

try:
	category_data = data[category]
except:
	logging.warning("No existing category '" + category + "', so we'll make a new one")
	category_data = {}


option = webdriver.ChromeOptions()
browser = webdriver.Chrome(executable_path='/usr/bin/chromedriver', chrome_options=option)

browser.get(start_url)

# Wait 10 seconds for page to load
timeout = 20

try:
	WebDriverWait(browser, timeout).until(EC.visibility_of_element_located((By.XPATH, "//a[@id='logo']")))
	logging.info("Successfully loaded landing page")
	
	while 'true':
	
	#print(json.dumps(data, indent=4, sort_keys=True))
		parse_landing_page(browser, category_data)
		
		logging.info("Writing to file")
		data[category] = category_data
		with open('data.json', 'w') as outfile:
			json.dump(data, outfile)
	
		try:
			next_page=browser.find_element_by_class_name('pager').find_element_by_class_name('next_page').get_attribute('href')
			logging.info("Next Page: " + next_page)
			sleep(10)
			browser.get(next_page)
		except:
			logging.info("No more pages")
			break
		
	data[category] = category_data
	with open('data.json', 'w') as outfile:
		json.dump(data, outfile)
	
except TimeoutException:
    logging.error("Timed out waiting for page to load")
finally:
	browser.close()