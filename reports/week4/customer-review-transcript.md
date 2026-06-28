## Meeting Recording – 27/06/2026 12:03:00

00:00:49 – Team Member 1:
Honestly, I’m not sure—he’ll explain that part. Regarding latency, I optimized everything as much as possible. Metrics that need to be updated frequently are recalculated with every new one-second candle. Metrics based on a 24-hour period are updated once per minute with every new one-minute candle.

00:01:19 – Customer 1:
Can you repeat that about the metrics?

00:01:22 – Team Member 1:
Sure. Metrics that change frequently, such as volatility or volume spike, are updated with every one-second candle. Metrics calculated over a 24-hour period, such as correlation, are updated once per minute because nothing significant changes within a single second for those statistics.

00:02:07 – Customer 1:
Sounds good.

00:02:10 – Customer 1:
Where do you store those metrics?

00:02:11 – Team Member 1:
All metrics are stored in our database.

00:02:17 – Customer 1:
So every second, when a new candle arrives, you update the metrics?

00:02:23 – Team Member 1:
Yes. Every one-second candle is written to the database.

00:02:30 – Customer 1:
Okay.

00:02:31 – Team Member 1:
Alright, I’ll start the screen sharing.

00:02:42 – Team Member 1:
Can everyone see it?

00:02:43 – Customer 1:
Yes, we can.

00:02:44 – Team Member 1:
Great. Team Member 2, could you explain what “No Reliable Pattern” means?

00:02:54 – Team Member 2:
I’ve started working on the machine learning component for pattern recognition. So far, I’ve completed one pipeline. At the moment, the ML model detects patterns only on one-minute candles using the previous 96 candles as input. Other timeframes are not supported yet.

00:03:29 – Customer 1:
From what I’ve heard, it’s difficult to detect meaningful patterns within just one minute.

00:03:39 – Team Member 2:
Not over a single minute. It’s based on one-minute candles covering approximately one and a half hours.

00:03:49 – Customer 1:
I see. Even over that period, another team mentioned yesterday that meaningful patterns are difficult to find. They may only appear once a month or so. You may want to experiment with increasing the analysis window.

00:04:16 – Team Member 2:
You mean increasing the duration of the pattern?

00:04:18 – Customer 1:
Exactly. Test different ranges, see how often patterns are detected, whether they’re detected correctly, and balance that against processing time. By the way, how will pattern detection work? If a pattern is found in the latest analyzed window, will it automatically appear in the panel on the right, or will users need to click something?

00:04:54 – Team Member 2:
It will appear automatically. Right now, though, the model has only been trained on artificially generated data with ideal patterns, not on real market data.

00:05:20 – Customer 2:
Where did you get those training data? Did you create them yourselves or use an existing dataset?

00:05:26 – Team Member 2:
We had them generated.

00:05:35 – Customer 2:
How do you plan to display detected patterns directly on the chart?

00:05:42 – Team Member 2:
That’s still under discussion. Usually analysts draw patterns manually.

00:06:02 – Customer 1:
Looking at your Figma designs, the widgets were positioned differently. How do you want to display detected patterns in the final version?

00:06:23 – Team Member 1:
How would you prefer to see them?

00:06:25 – Customer 1:
What ideas do you already have? Different pattern types may require different visualizations. You’re planning to detect geometric patterns, correct?

00:06:50 – Team Member 2:
Yes.

00:06:51 – Customer 1:
Then you should think about how each pattern can be displayed clearly on the chart. You could mark the boundaries where the pattern was found or find another intuitive visualization.

00:07:06 – Team Member 2:
For example…

00:07:10 – Customer 2:
Besides simply displaying the pattern name in a side panel, think about the UX. Users should clearly understand where the pattern was detected and what it represents.

00:07:30 – Team Member 1:
So basically the model predicts the pattern, and then we draw it on the chart.

00:07:37 – Customer 1:
Exactly. The ML model only predicts it. Visualization is your responsibility.

00:07:46 – Team Member 1:
Understood.

00:07:50 – Team Member 2:
Converging patterns, for example, could be shown using two lines. Head-and-shoulders could use three key points. Each pattern probably deserves its own visualization style.

00:08:43 – Customer 1:
Your candlestick chart displays live market data, right? Which API are you using?

00:09:00 – Team Member 1:
Binance and Bybit.

00:09:53 – Customer 1:
How does the backend receive updated data?

00:10:00 – Team Member 1:
Through GET requests.

00:10:04 – Customer 1:
So the frontend sends requests every minute?

00:10:11 – Team Member 1:
As far as I remember, yes.

00:10:12 – Customer 1:
Okay. What about latency?

00:10:17 – Team Member 1:
The Last Price value and similar indicators update in about 100 milliseconds. Metrics, except the 24-hour ones, are updated with every completed one-second candle.

00:11:09 – Customer 1:
I’m just wondering how close your chart is to real-time.

00:11:10 – Team Member 1:
You mean its accuracy?

00:11:14 – Customer 1:
Yes, how much delay there is.

00:11:20 – Team Member 1:
That’s difficult to estimate precisely. We’ve collected a lot of diagnostic information. The interface still looks messy because it’s mainly for testing. But the collected statistics will help us reduce latency in the future.

00:12:13 – Customer 1:
Okay.

00:12:14 – Team Member 1:
Currently, Last Price updates within roughly 100 milliseconds. The live candle updates within 100–300 milliseconds plus exchange network latency. The finalized candle appears about two seconds after the candle closes because we wait for delayed trades to arrive to ensure consistency with the exchange.

00:13:18 – Customer 1:
Do you receive Binance data through WebSockets?

00:13:28 – Team Member 1:
Yes.

00:13:30 – Customer 1:
Great.

00:13:31 – Team Member 1:
Historical candles can only be downloaded as one-minute candles. Binance doesn’t provide historical one-second candles, so we generate them ourselves in real time.

00:14:12 – Customer 1:
That means data below the one-minute timeframe may be less accurate, while one-minute and above should fully match Binance and Bybit.

00:14:38 – Customer 1:
Customer 2, do you have any questions?

00:14:41 – Customer 2:
No. Everything looks nice and convenient.

00:14:46 – Team Member 2:
Okay. Anything else?

00:14:49 – Customer 1:
Let’s discuss the ML component in more detail. What’s currently implemented?

00:14:54 – Team Member 1:
That’s Team Member 2’s area. I was focused on latency optimization.

00:15:04 – Customer 1:
Regarding your generated training data—I’d recommend switching to publicly available datasets because synthetic data may introduce bias. There should be datasets available for the most popular cryptocurrencies.

00:15:36 – Team Member 2:
I agree. I’ve only built the initial pipeline so far. The main goal was to evaluate and select the appropriate model before proper training.

00:16:08 – Customer 1:
Will detected historical patterns also be stored in the database?

00:16:20 – Team Member 1:
Yes. We plan to store as much information as possible because it will help improve the model.

00:16:30 – Customer 1:
How large is your database currently?

00:16:38 – Team Member 1:
Locally, I loaded 100 days of minute-level data for both exchanges across 20 charts. It occupied roughly 1 GB, so storage requirements are quite reasonable.

00:17:12 – Customer 1:
Makes sense. Anything else you’d like to demonstrate?

00:17:14 – Team Member 1:
Yes, we’d like to validate our User Stories by letting you test the application.

00:17:24 – Customer 1:
We’ve already tested it ourselves. Everything looks good. Customer 2?

00:17:29 – Customer 2:
Yes, I like it.

00:17:32 – Team Member 1:
Let’s register a new user for demonstration purposes.

(Demonstrates registration and login.)

00:18:10 – Customer 1:
You misspelled “Yandex.”

00:18:14 – Team Member 1:
Really?

00:18:15 – Customer 1:
Yes.

00:18:18 – Team Member 1:
Just a typo.

00:18:23 – Customer 2:
Now try entering the wrong password.

00:18:15 – Team Member 1:
Oops, I entered an extra digit. Now it’s corrected, and authorization succeeds. The chart loads correctly. We also have a “Load Earlier” button that loads approximately 1,500 candles each time. Metrics are calculated, signals appear—for example, RSI Extreme.

00:19:33 – Team Member 2:
We also wanted to verify the User Stories. The dashboard and analytics output have already been demonstrated. We also support handling backend failures.

00:20:00 – Team Member 1:
If the backend is unavailable, the frontend displays a warning that the backend is unreachable and hides live data so users don’t see outdated information.

00:20:47 – Customer 1:
How do you detect backend failures?

00:20:50 – Team Member 1:
The frontend checks whether the backend connection is still alive.

00:20:58 – Customer 1:
If a request fails, you show that message?

00:21:01 – Team Member 1:
Yes.

00:21:04 – Customer 1:
Which request? A health check or regular data requests?

00:21:09 – Team Member 1:
Actually, I misspoke earlier. We don’t use GET requests anymore.

00:21:12 – Customer 1:
You mentioned GET before.

00:21:16 – Team Member 1:
Everything uses WebSockets now.

00:21:19 – Customer 1:
So if no data arrive for a while, you consider the backend unavailable?

00:21:26 – Team Member 1:
Exactly.

00:21:50 – Team Member 1:
Here’s Grafana. We’re collecting latency metrics on the virtual machine. Some delays currently look very high—several minutes—which we’ll investigate further.

00:22:30 – Team Member 2:
It’s probably not caused by trading activity.

00:22:33 – Team Member 1:
We can also see periods when no trades occurred for specific assets.

00:22:50 – Customer 1:
Good job. The main remaining task is improving the ML model and getting its accuracy as high as possible. You’ll also need a clear visualization for detected patterns.

00:23:20 – Team Member 2:
Regarding CI, I’ve already added tests for analytics, indicators, candlestick generation, ML, authentication, aggregation, live data, and registration. I also integrated Gitleaks to detect leaked secrets and configured CI in GitHub.

00:25:20 – Customer 1:
I see two failing checks.

00:25:25 – Team Member 2:
Yes, one small backend fix is still needed. I’m also investigating the secret scan issue. This is only a pull request and hasn’t been merged yet.

00:25:37 – Customer 1:
Understood.

00:25:40 – Team Member 2:
Should we add any additional tests?

00:25:47 – Customer 1:
Just maximize the coverage. The tests you listed are mainly unit tests, right?

00:25:52 – Team Member 2:
We have unit tests, integration tests, backend QA tests, Gitleaks security checks, and more.

00:26:03 – Customer 1:
Just keep increasing the coverage as much as possible. Also verify that AI-generated tests are actually meaningful and not simply validating mocked data without real value.

00:26:40 – Team Member 2:
I think that’s everything. Team Member 1, anything else?

00:26:46 – Team Member 1:
Just one final question. Were you satisfied with today’s demonstration? We need this feedback for our documentation. Apart from the ML component, is there anything you’d like us to improve?

00:27:14 – Customer 1:
Yes, everything looked good. Please put your main focus on improving the ML component.
