import scrapy
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.options import Options
from scrapy.utils.project import get_project_settings
from dviz_oluwaseyi.items import DvizOluwaseyiItem
from selenium.webdriver.common.by import By
import json
from collections import MutableMapping
from datetime import datetime

settings = get_project_settings()

radius = ""
zipCode = ""
radiusRange = list(range(25, 501, 25)) + [5000]
baseUrl = f"https://www.tred.com/buy?body_style=&distance={radius}&exterior_color_id=&make=&miles_max=100000&miles_min=0&model=&page_size=24&price_max=100000&price_min=0&query=&requestingPage=buy&sort=desc&sort_field=updated&status=active&year_end=2022&year_start=1998&zip={zipCode}"
xpath = "//div[@class='grid-car col-md-4 col-sm-6 col-xs-6']//div[@class='card']//div[@class='grid-box-container']//a"
apiEndpoint = f"https://www.tred.com/api/listings/"
dateTimeString =datetime.now().strftime("%m_%d_%Y_%H_%M")

while True:
    radius = input(f"Please choose your desired radius from the list {radiusRange}: ")
    if int(radius) not in radiusRange:
        radius = ""
        print("Error: Please select a radius value for the displayed range {radiusRange}: ")
        continue
    break

while True:
    zipCode = input(f"Please input Zip Code digits in the format xxxxx: ")
    if not zipCode.isdigit():
        print("Please input valid Zip Code Digits only: ")
        continue
    break


def flattenDictionary(mydict, parent_key ='', sep ='_'):
    """this unction for flattenes deeply nested dictionaries found in API response
    body using Collections module MutableMapping with recursion"""

    items = []
    for k, v in mydict.items():
        new_key = parent_key + sep + k if parent_key else k
 
        if isinstance(v, MutableMapping):
            items.extend(flattenDictionary(v, new_key, sep = sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

class TredCarsSpider(scrapy.Spider):
    """Scrapy Siper Class"""
    name = 'tred_cars'
    custom_settings = {
        'AUTOTHROTTLE_ENABLED': True,
        'DOWNLOAD_DELAY': 0.5,
        'DEPTH_LIMIT': 1,
        "FEEDS":{f"results/results_{dateTimeString}.csv":{"format":"csv"}}
    }

    def start_requests(self):
        """This function integrates selenium for getting a response from the base URL defined above
        by send parsing the values of the radius and zipcode provide into the base URL sttring and calling the endpoint.
        The XML path defined above to traverse the HTML documents returned to get the links for all displays cars"""

        options = ChromeOptions()
        options.headless = True
        driver = Chrome(executable_path=settings.get("CHROME_DRIVER_PATH"), options=options)
        driver.get(baseUrl)
        cars = driver.find_elements(By.XPATH, xpath)

        for car in cars:
            vin = car.get_attribute("href").split('?')[0].split('/')[-1] #Obtain vin from generate URL
            yield scrapy.Request(apiEndpoint+vin)
        
        driver.quit()

    def parse(self, response):
        data = json.loads(response.body) 
        item = DvizOluwaseyiItem()
        item["name"] = f"{data['year']} {data['make']} {data['model']}"
        item["price"] = f"{data['price']}"
        item["vehicleSummary"] = {"VIN": data.get('vin'),
                                    "Trim": data.get('trim'),
                                    "Full Style Name": data.get('full_style_name'),
                                    "Mileage": data.get('mileage'),
                                    "Tire Mileage": data.get('tire_mileage'),
                                    "Transmission": data.get('specs').get('transmission'),
                                    "Drive Type": data.get('specs').get('drivetrain'),
                                    "Engine": f"{data.get('specs').get('engine').get('horsepower').get('value')}HP @ {data.get('specs').get('engine').get('horsepower').get('rpm')} RPM {data.get('specs').get('gas').get('cylinders')} cylinder, {data.get('specs').get('gas').get('displacement')}L",
                                    "Fuel Economy": f"{data.get('specs').get('fuelEconomy').get('city')}MPG city, {data.get('specs').get('fuelEconomy').get('highway')}MPG highway, {data.get('specs').get('fuelEconomy').get('combined')}MPG combined",
                                    "Doors": data.get('specs').get('doors'),
                                    "Passengers": data.get('specs').get('passengerCapacity'),
                                    "Exterior": data.get('exterior_color_id')
                                    }
        item["vehicleOptions"] = []

        for val in data.get('specs').get('options').get('equipment'):
            optionData = flattenDictionary(data.get('specs').get('options').get('equipment').get(val))
            item["vehicleOptions"].append(optionData.get('optionGroups')[0].get('options')[0].get('name'))

        yield item