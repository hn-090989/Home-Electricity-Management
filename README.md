# Home-Electricity-Management
Video Demo: 

Project description: 
For my Cs50x final project, I decided to build a home electricity management system which allows users to track their electricity usage.Users can see their power consumption throughht the moth, week and day. Furthermore, it allows them to check and monitor each of their appliances' usage independently. The bill for each month is also generated. 

**management.db**

This file contains the sql database that is used to store the data of all the users that have registered. It contains: a users table that stored the password names and ids of all the users; a power_logs table that contains logs for every user that is consuming power. Each log stores the id of the user, the appliance that consumed the power as well as the the time at which the data was logged; an appliances table stores the data for the appliances registered by the users. It contains the id of the user that registered it as well as the name of the appliance and its wattage; lastly, the billings table has monthly data that stores the bill generated and the power consumed by the user throught the month. 

**Dahboard**

The dashboard is the default page the user reders if they are logged in. It is accessed using the "/" route. The route renders the dasboard.html page with all the ststic info that it needs, the info that only records changes when the user re loads the page. This includes this months, todays and this week's total agrregated powerconsumption this power consumption is queried from management.db but aggregating the required logs. The bill generated so far for the current month is alsi calculated using pakistans current tariff rates. If the user has used the app for more than a yaer than the page will also display last years bill at the same month as well as the units consumed. 
Next we have the graphs. The graphs are generated using charts.js. There are 3 graphs: power consumed this month, this week and today. The graphs update every 30 seconds via an update function in the javascript. The update function calls the get_data flask route to get the data from the sql tables. The data values and labels of the graph are then plotted using the received data. 

**Appliances**

The appliances page contains the appliance wise breakdown of the power consumption. The static data, that is only changed on reload, are the top three appliances and the pie chart containing the average power consumed by each appliance in the current month so far. The page is redered via the "/appliances" route in app.py. The route also sends in data for the pie chart and the top 3 aoppliances via SQL queries. It also sends a list of the appliances that are registered by the logged in user. The list of appliances is used in the html to define the options in a select html tag. The user can select an appliance and the line grapg below it will render the data for the selected appliance. This is done using fetch requests like done in the Dahboard. Whenever the user changes the appliance the javascript will fetch data from the route "/get_appliances_data". This route checks the users option and sends back data accordingly. The graph is then updated and renders the users selected appliance. 
At the bottom of the page is a list of appliances. Here the user can update or delete an existing appliance or add a new one. All these are done using different fetch requests and different routes. The routes in app.py will then update management.db and send sucess true after which the page will update automatically without a reload.

**Billing**

The billings page shows the bills of all the previous months as well as wether the user has payed the bill yet or not. This page does not have the exact iplementation i hoped for, but it id satisfoactory considering my current knowledge. The "/billing" route first checks to see if the bill has been generated for the previous month or not via the bill_generation_check() function. If it has, the route will return a list of all the users previous bills in the SQL bills table. If it hasnt, the route will generate a bill using the generate_user_bill() fuction. This is done using the sum of all the logs in the power_logs table for the last month and miltiplying them by the tariff rates. The bill is then inserted into the bills table. 

**Register**

The register page asks the user for their name, username password and email. All of these are required feilds. The html checks if the user had typed in the field using the required tag in the input tag. The backend "/register" route also confirms this by getting the inputs of the submitted form and checking if all the feilds have been typed in. If the form is submitted without all the feilds being filled and the username is not already present in the users table, the user is rediredted to the login page. If all the fields hae been filled, it adds the user to the users table and directs them to the dashboard. The hash of the password is generated using the generte_password_hash() function. 


**Login** 

The login page asks for a username and password. It has the same checks to verify user input as the Register page. The "/login" had two methods. If the user submits the form, the code under the post request is used. On submiting the form, the route gets the user inputs and checks to see of the user exits in the users table. If yes, the user is redirected to the "/" route that loads the Dashboard. If not, the login page is rendered again. 

**datagenerator.py**

This is the python file that was used to create the dummy data used to show the functionality of the web app. It generated the data for 3 months for all the appliances included in the demo. The start and end times are defined using the datetime() function. The batch variable is a list tupes. The the while loop, the random function generates random data for the appliance. The data is then appended to the list batch. After 1000 enteries of data the data is inserted into the power_logs table. After the loop ends, there might be less than 1000 rows left, ao there is another if function that adds the remaining data to the power_logs table.

**helpers.py**

This code defines a Flask decorator called login_required that ensures a user is logged in before accessing certain routes. login_required is a decorator function that takes a function f as input. It checks if the user is logged in. If the user is logged in, it runs the original function present below the route. If not, it returns a decorated function. 


Improvements






