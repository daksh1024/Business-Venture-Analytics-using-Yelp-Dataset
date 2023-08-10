# business-analyzer

In today's dynamic and competitive business landscape, making informed decisions is vital
for entrepreneurs and businesses to prosper and flourish. The success of any venture depends
on a deep understanding of customer preferences, market trends, and the suitability of a location
for a specific business category. With the exponential growth of the digital age, customers have
more power than ever before, and their satisfaction plays a crucial role in shaping businesses'
destiny.
The objective of our project is to tackle this urgent requirement by providing businesses
with valuable analytics to help them make well-informed choices about the feasibility of opening
new ventures in specific cities, locations, and business categories. This project focuses on creating
a web-based application that utilizes cloud database infrastructure and interactive visualizations
to provide valuable information about customer satisfaction, popular business attributes, and
the performance of various companies.

##To start the application
1. To save on the server usage, we have stopped the BigQuery instances, however, the datasets can be downloaded from the yelp dataset website (https://www.yelp.com/dataset). Save the BigQuery credentials in the credentials.py file.
2. Create a local python virtual environmant. Initialize new local git repository using git init command. Clone this repository.
3. Install all the packages from requirements.txt file.
   
   pip install -r requirements.txt
   
4. Run the application using the following command.
   
   flask --app index run

