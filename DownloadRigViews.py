from lxml import html
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium import webdriver
import os
import time
import random
import psycopg2

#Init selenium webdriver
webdriver = webdriver.PhantomJS(os.path.join(os.path.dirname(__file__),'bin/phantomjs'))
wait = WebDriverWait(webdriver, 10)
#Load credentials
credentials = {'username':os.environ['USERNAME'], 'password':os.environ['PASSWORD']}

MAIN_PAGE_URL = 'https://www.rmoj.com/membersonly/RigSpotter.aspx'

def get_additional_info(spans,div_contents):
    def hasNumbers(inputString):
        return any(char.isdigit() for char in inputString)

    def filter_sub_section(items):
        for item in items:
            sub_items = item.split(' ')
            for sub_item in sub_items:
                if '-' in sub_item:
                    splitted = sub_item.strip().split('-')
                    if len(splitted) == 2 and len(splitted[0]) == 2 and len(splitted[1]) == 2 and not hasNumbers(splitted[0]) and not hasNumbers(splitted[1]):
                        return sub_item.strip()
        return None

    return (filter_sub_section(div_contents),datetime.strptime(spans[-1].strip(), '%m/%d/%y'))

def extract():
    # Get main table and select all urls to items pages
    table_content = webdriver.find_element_by_id('ctl00_ContentPlaceHolder1_GridView1').get_attribute('innerHTML')
    document = html.fromstring(table_content)
    count = len(document.xpath('.//tr[position()>1 and position()<last()]/td[position()=1]'))
    links = ["__doPostBack('ctl00$ContentPlaceHolder1$GridView1','Select$%s')" % i for i in range(count)]
    trs = document.xpath('.//tr[position()>1 and position()<last()]')

    # Adding information from the main page
    items = []
    for tr in trs:
        d = {}
        tds = tr.xpath('.//td[position()>1]//text()')
        d['contractor'] = tds[0]
        d['number'] = tds[1]
        d['operator'] = tds[2]
        d['well_num_name'] = tds[3]
        d['basin'] = tds[4]
        d['county'] = tds[5]
        d['state'] = tds[6]
        d['section'] = tds[7]
        d['township'] = tds[8]
        d['range'] = tds[9]
        d['pd'] = tds[10]
        d['status'] = tds[11]
        d['notes'] = tds[12]
        d['date_scraped'] = datetime.now()
        well_num_name = d['well_num_name'].split(' ')
        well_name = ''
        well_num = ''
        i = 0
        for ind, part in enumerate(well_num_name):
            if '-' not in part:
                well_name += part + ' '
            else:
                i = ind
                break

        well_num = ' '.join(well_num_name[i:-1]) + ' ' + well_num_name[-1]
        d['well_name'] = well_name.strip()
        d['well_num'] = well_num.strip()
        items.append(d)

    # Iterating thru items pages
    for i, link in enumerate(links):
        webdriver.execute_script(link)
        # Redirecting is processing by javascript, so we have to wait while page is downloading
        wait.until(
            expected_conditions.presence_of_element_located(
                (By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_FormView1_PanelForEditTemplate']"))
        )
        html_content = webdriver.find_element_by_id('pubnavcontent').get_attribute('innerHTML')
        document = html.fromstring(html_content)
        spans = document.xpath("//span[@class='roform']//text()")
        div = list(filter(None, document.xpath("//div[@class='previewborder']//text()")))
        items[i]['sub_section'], items[i]['updated'] = get_additional_info(spans, div)
        webdriver.back()
        time.sleep(random.randint(2, 15))

    return items

def insert_into_database(items):
    with psycopg2.connect(database="data",user="ag",host="138.68.81.207",port=5432,password=os.environ['DATABASE_CRED']) as connection:
        cursor = connection.cursor()

        for d in items:
            table_names = ', '.join(list(d.keys()))
            values = ', '.join(['%s' for i in list(d.values())])
            qry = "INSERT INTO rigs (" + table_names + ") VALUES (%s) " % values
            d_c = d.copy()
            del d_c['contractor']
            del d_c['number']
            del d_c['well_num_name']
            del d_c['well_name']
            del d_c['well_num']
            cursor.execute(qry, list(d.values()))

        connection.commit()

def main():
    items = []

    #Log in
    webdriver.get(MAIN_PAGE_URL)
    webdriver.find_element_by_id('ctl00_ContentPlaceHolder1_Username').send_keys(credentials['username'])
    webdriver.find_element_by_id('ctl00_ContentPlaceHolder1_Password').send_keys(credentials['password'])
    webdriver.find_element_by_name('ctl00$ContentPlaceHolder1$ctl04').click()

    #Set items to show = 100
    webdriver.find_element_by_xpath("//select[@name='ctl00$ContentPlaceHolder1$GridView1$ctl13$ctl11']/option[text()='100']").click()
    #Getting number of pages
    page_number = len(webdriver.find_elements_by_xpath("//tr[@class='grid-pager']//table//tr/td[not(@class)]"))
    page_href_script = "__doPostBack('ctl00$ContentPlaceHolder1$GridView1','Page$%s')"

    #Extracting each page on the website
    for i in range(page_number):
        i += 1
        if i != 1:
            webdriver.execute_script(page_href_script % i)
            # Wait for redirecting
            time.sleep(10)
        items += extract()

    #Insert into database all extracted items (rigs)
    insert_into_database(items)

if __name__ == '__main__':
    print('Cron job started')
    main()
    print('Cron job is over')