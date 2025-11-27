#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
import pandas as pd


def fetch_jobs(output_file="data_scraped.csv", url=None):
    df = pd.DataFrame()
    df_dict = {
        'cargo': [],
        'empresa': [],
        'salario_base': [],
        'localizacao': [],
        'descricao': [],
        'link': []
    }
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    driver.get(url)

    time.sleep(4)

    consecutive_errors = 0

    i = 0
    try:
        while True:
            # Re-encontra os cards a cada loop para pegar os novos carregados
            cards = driver.find_elements(By.CSS_SELECTOR, ".jobCard")
            
            # Se já processamos todos os cards visíveis e não carregou mais nada após tentativas, paramos
            if i >= len(cards):
                consecutive_errors += 1
                if consecutive_errors > 3:
                    print("Fim da lista ou não foi possível carregar mais itens.")
                    break
                time.sleep(2)
                continue
            
            # Reset consecutive errors when new cards are found
            consecutive_errors = 0
            
            card = cards[i]

            link_el = card.find_element(By.CSS_SELECTOR, "a.JobCard_trackingLink__HMyun")

            href = link_el.get_attribute("href")

            print(f"Acessing {href}.\n i = {i}")
            # click on show more btn
            try:
                show_more_btn = driver.find_element(By.CSS_SELECTOR, ".ShowMoreCTA_showMore__EtZpZ")
                show_more_btn.click()
            except:
                pass

            # if do not have salary, step forward
            try:
                salary_el = card.find_element(By.CSS_SELECTOR, ".SalaryEstimate_medianEstimate__fOYN1")
                salary_text = salary_el.text
                df_dict['salario_base'].append(salary_text)
            except: 
                i += 1 
                continue
            
            # get job cargo
            try:
                cargo_el = driver.find_element(By.CSS_SELECTOR, ".heading_Heading__aomVx.heading_Level1__w42c9")
                df_dict['cargo'].append(cargo_el.text)
            except:
                df_dict['cargo'].append(None)

            # get company name
            try:
                company_el = driver.find_element(By.CSS_SELECTOR, ".heading_Heading__aomVx.heading_Subhead__jiUbT" )
                df_dict['empresa'].append(company_el.text)
            except:
                df_dict['empresa'].append(None)

            # get location
            try:
                location_el = driver.find_element(By.CSS_SELECTOR, ".location")
                df_dict['localizacao'].append(location_el.text)
            except:
                df_dict['localizacao'].append(None)

            # get job description
            try:
                desc_el = driver.find_element(By.CSS_SELECTOR, ".JobDetails_jobDescription__uW_fK.JobDetails_showHidden__C_FOA")
                df_dict['descricao'].append(desc_el.text)
            except:
                df_dict['descricao'].append(None)

            df_dict['link'].append(href)

            time.sleep(2)
            i += 1
    except:
        df = pd.DataFrame(df_dict)
        df.to_csv(output_file, index=False)

if __name__ == "__main__":
    fetch_jobs("./../../data_test/jobs.csv")