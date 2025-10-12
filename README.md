# Project Name: Veritas News

## Members: Jack Webster, Aadity Sharma, Yann Calvo-Lopez, Vineet Jammalamadaka

## Google Drive Link: https://drive.google.com/drive/folders/16DhHYGhWOP0-UIXO258NQ7Z6VN5TJmlq?usp=drive_link

### Project Overview
News aggregation and synthesis platform to deliver real time updates on world news while highlighting differing perspectives and potential biases. 

The core features of our application will include a news feed which will aggregate news articles through web scraping / api integration and provide an estimated bias rating and a summary of differing perspectives for each news topic. The application will also provide references / links to primary sources when relevant to indicate potential misinformation or contradictory information. 

Additionally the product will allow users to open any news article within the context of the application, to gain further insight into the potential bias of the article and engage with other articles on the topic.  
To standardize scoring, the application will ask an LLM / API to consider a set of core questions, for example: 
Does the article implicitly or explicitly support positions associated with progressive or conservative policy agendas? (What language / quotes support this)
Does the article use emotionally charged wording in favor of one side?
Issue emphasis: Which issues are prioritized (e.g., immigration, climate, taxation), and how are they framed? (What language / quotes support this?)
Does the article portray any underlying values (individual freedom, social justice, tradition, markets) more aligned with one end of the spectrum?
