# DY Capital
#### Video Demo: https://youtu.be/TzKK3c2T5Do

#### Description:
This is an all-around simulated stock trading web application. 

The aim is to provide a tool for those interested in high finance to start working their way into it by making risk-free simulated bets on stocks. The application runs on the PostgeSQL server so its data persists on Heroku; it can hence be used for both short term (trading) and long term (investing) bets. 

The homepage displays the current “Word on The Street” which comprises a list of headlines about the hottest stories making rounds on Wall Street and the greater finance community. The headlines are links to the detailed stories. 
It is here that users can get insights into what stocks to consider for buying, selling, or holding. 
The code behind it is housed in app.py (/), helpers.py, news.html, and newsloggedin.html. 

The portfolio page displays all the stocks being held by the user and their current prices on the market. 
The page also shows the user’s profitability position through a profitability box. The profitability box displays both the percentage loss/profit and the dollar amount of the loss/profit. 
It flashes red when the user is in losses, and radiates blue when the times are good. 
It is here that users will find out that finance isn’t for the weak, and that fortunes can be lost just as easily as they are made. 
The code behind the page is housed in app.py (/portfolio), helpers.py, portfolio.html, and emptyportfolio.html. 

The quote page allows the user to query any stock on the market and get its relevant numbers, the most notable one being the prevailing price. 
The other metrics shown include: the company’s market capitation, earnings per share, the future expected earnings per share, dividend yield, and price-to-earning multiples. These are amongst the most important parameters used by the pro investors and traders when evaluating stocks. 
When the information got on this page is combined with the “Word on The Street”, the user is armed with a flashlight to navigate the dark murky world of stocks. 
The code behind this page is housed in app.py (/quote), helpers.py, quote.html, and quotation.html. 

The buy and sale pages are where the user puts their ‘money’ or stock where their mouth is. It is where the trades are triggered. 
The code behind these pages are housed in app.py (/buy and /sell), helpers.py, buy.html, and sell.html. 

The history page is a ledger of all the trades made by the user. The hope is that upon scrolling through it, one acknowledges the journey they have had from a hopeful ecstatic novice to a hardened, sto(ne)ke cold master weary of anything that seems a little too good. 
The code behind this page is housed in app.py (/history), history.html, and emptyhistory.html.

