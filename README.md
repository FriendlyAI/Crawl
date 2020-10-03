Crawl: Reddit Scraping and Analysis
===================================

Info
----

This project is aimed at providing useful and interesting metadata analysis from the huge diversity of users of
reddit.com. It uses the PRAW module, which is outside Python’s default set of modules, to scrape data from users and
submissions on reddit using their API, which allows authorized access of data. Through a GUI, a user can choose an
arbitrary number and combination of users and subreddits to scrape data from, with top comments and posts from these
sorted in any order. Python’s regular expressions module is used to match URLs and tags to ignore, leaving only actual
words. A text file of commonly used words such as conjunctions and prepositions is used to create a set of stopwords,
which are also ignored during analysis. The resulting list of words is funneled into a dictionary to count the frequency
of each word. During visualization, the commonality of the top words for the specific user or subreddit is counted and
represented as circles of different radii, sorted by largest. The project also counts the types of links submitted to a
subreddit or by a user, and is graphed as a proportion simultaneously during visualization for each user/subreddit
analyzed for comparison. The corpus of each user and subreddit is also scraped, and is used to generate simulated
sentences by a specific user or users of a subreddit using a Markov Chain, which uses Python’s random module. The user
can continuously generate these simulated sentences during visualization.

Parts of the project include functions that are timed for logging use, and use Python’s time module.

Make sure to run in UTF-8 encoding to prevent crashes from non-ascii characters.
This must be manually done in IDLE and some IDEs.

Installation
------------

Dependencies:

- PRAW

Recommended: 
`pip install praw`

Also available at https://github.com/praw-dev/praw.
