import unittest
import time
import sys
from selenium import webdriver
from flask_testing import LiveServerTestCase
from datetime import datetime
sys.path.append('..')
from app import app


class TrialTest(LiveServerTestCase):
    def create_app(self):
        front = app
        front.config['TESTING'] = True
        front.config['DEBUG'] = False
        self.user = 'user_%s' % datetime.now().strftime('%d_%b_%H_%M')
        self.password = 'password123'
        return front

    @classmethod
    def setUpClass(cls):
        cls.browser = webdriver.Firefox()

    def test_basic_workflow(self):

        # User Signup
        self.browser.get(self.get_server_url())
        new_user_name = self.browser.find_element_by_id('signup_username')

        new_user_name.send_keys(self.user)
        new_user_password = self.browser.find_element_by_id('signup_password')
        new_user_password.send_keys(self.password)
        submit_button = self.browser.find_element_by_id('submit_signup')
        submit_button.click()
        time.sleep(2)

        # User Select RolegroupID
        welcome_message = self.browser.find_element_by_id('welcome_message').text
        self.assertTrue(self.user in welcome_message)

        roles = self.browser.find_elements_by_css_selector('h4.card-title')
        roles = [i.text for i in roles]
        self.assertTrue(roles == ['Data_Science', 'DevOps'])
        ds_selector = self.browser.find_element_by_id('1')
        self.assertTrue(ds_selector.get_attribute('value') == '1')
        ds_selector.click()

        submit_button = self.browser.find_element_by_id('submit_rolegroup')
        submit_button.click()
        time.sleep(4)

        # User starting view
        jobs_container = self.browser.find_element_by_css_selector('div.jobs-container')
        self.assertTrue(jobs_container.get_attribute('id') == 'nov_2019')

        jobs_list = jobs_container.find_elements_by_css_selector('li.list-group-item')
        job_ids = [i.get_attribute('id') for i in jobs_list]
        self.assertTrue(job_ids == ['2', '1', '3', '4', '6', '5'])

        # User acts on 2 jobs
        jobs_container.find_element_by_id('nov_2019|2|1').click()
        jobs_container.find_element_by_id('nov_2019|1|2').click()

        # Verify first job
        self.browser.find_element_by_id('navigate_1').click()
        time.sleep(2)

        jobs_container = self.browser.find_element_by_css_selector('div.jobs-container')
        self.assertTrue(jobs_container.get_attribute('id') == 'nov_2019')

        jobs_list = jobs_container.find_elements_by_css_selector('li.list-group-item')
        job_ids = [i.get_attribute('id') for i in jobs_list]
        self.assertTrue(job_ids == ['2'])

        # Verify second job
        self.browser.find_element_by_id('navigate_2').click()
        time.sleep(2)

        jobs_container = self.browser.find_element_by_css_selector('div.jobs-container')
        self.assertTrue(jobs_container.get_attribute('id') == 'nov_2019')

        jobs_list = jobs_container.find_elements_by_css_selector('li.list-group-item')
        job_ids = [i.get_attribute('id') for i in jobs_list]
        self.assertTrue(job_ids == ['1'])

        # Logout
        self.browser.find_element_by_id('logout').click()
        time.sleep(1)

        # Login again
        self.browser.find_element_by_id('login_tab').click()
        new_user_name = self.browser.find_element_by_id('login_username')
        new_user_name.send_keys(self.user)
        new_user_password = self.browser.find_element_by_id('login_password')
        new_user_password.send_keys(self.password)
        submit_button = self.browser.find_element_by_id('submit_login')
        submit_button.click()
        time.sleep(2)

        # Check view
        jobs_container = self.browser.find_element_by_css_selector('div.jobs-container')
        self.assertTrue(jobs_container.get_attribute('id') == 'nov_2019')
        jobs_list = jobs_container.find_elements_by_css_selector('li.list-group-item')
        job_ids = [i.get_attribute('id') for i in jobs_list]
        self.assertTrue(job_ids == ['3', '4', '6', '5'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()


if __name__ == '__main__':
    unittest.main()
