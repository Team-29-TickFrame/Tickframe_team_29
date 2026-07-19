# Customer Review Transcript
00:03:49 — Customer 1: Well, there we go. Oh, everyone is here. Okay, yes, everyone is here.

00:03:56 — Customer 1: Go ahead, tell us what you have. Well, what is there to tell us in general?

00:04:00 — Team Member 1: There is nothing to demonstrate yet, but I will finish it today. I am already freezing. Anyway, we also added another tab to the website.

00:04:11 — Team Member 1: It will contain all the scripts that might be useful, so that you do not have to search for them through the files, roughly speaking, and so that you can run them directly from the frontend.

00:04:18 — Customer 1: Which scripts?

00:04:19 — Team Member 1: For example, loading historical candles. For example, suppose you want to have a huge database containing data from the last three years. You will be able to run a script that will load all of that for you.

00:04:35 — Customer 1: Uh-huh.

00:04:36 — Team Member 1: Right.

00:04:37 — Customer 1: Okay.

00:04:38 — Customer 1: And what about the ML component?

00:04:40 — Team Member 2: The ML component? Well, I fixed it. We had a bug where sometimes a pattern was displayed, but there was no visualization. Now there is either a pattern and a visualization—or, more precisely, a recognized pattern and its visualization—or nothing at all.

00:04:59 — Customer 1: What was the problem?

00:05:01 — Team Member 2: The problem was that, as we discussed, the data returned by the ML model is not sufficient to construct the pattern. There is a check using the rule-based detector and the recognized labels. How should I put it? In English it is called “entrance,” something like anchors based on labels.

00:05:29 — Team Member 2: And then the structure is built using the vertices and the neckline. The problem was that sometimes the ML model recognized something, but the rule-based detector did not accept it. In other words, the recognized labels did not match, and therefore there was no visualization.

00:06:05 — Team Member 2: Hello? For some reason I cannot hear anyone right now.

00:06:11 — Team Member 2: By the way, I saw the question. I do not know whether…

00:06:30 — Customer 1: There was a question, Ivan. There was a question.

00:06:38 — Customer 1: Why did that happen if, in fact, the ML model was trained on the data provided by the rule-based system? Why did the rule-based system not accept what the ML model found?

00:06:49 — Team Member 2: Well, the ML model is not exactly one hundred percent rule-based. It works differently. The rule-based detector uses certain criteria. How does it work? For example, the rule-based detector is simply code. For a double bottom, for example, it finds certain vertices—candles that represent local minima and local maxima.

00:07:22 — Customer 1: Yes, I understand. No, the question is specifically this: look, if we said that the rule-based system is the master system, why should we show data if we originally relied on the claim that it provides one hundred percent accuracy? Why should we show those candles then?

00:07:39 — Customer 1: You said that the problem was that the ML model found some patterns, but the rule-based detector did not accept them. Because of that, they were not drawn on the frontend.

00:07:52 — Customer 1: Why, then, do we assume that the ML model produced the correct result and the rule-based detector did not, if everything was originally based on the assumption that the rule-based detector had maximum accuracy?

00:08:05 — Team Member 2: First of all, in a real market, a pattern does not always look perfect. The ML model is intended as an addition, so if the rule-based detector does not see something, perhaps…

00:08:17 — Customer 1: But we trained it using the data produced by the rule-based system.

00:08:21 — Team Member 2: No, it is not simply reproducing the rule-based code. It already makes decisions based on its own indicators…

00:08:27 — Customer 2: No, but what was your ML model trained on? For some reason, I thought that it was not trained on the rule-based data, but on something else.

00:08:37 — Customer 2: And the rule-based system was only used for double-checking. Or am I wrong?

00:08:43 — Team Member 2: Yes, it was used for double-checking, and the initial labeling was also performed using it.

00:08:50 — Customer 1: Well, then it means that the initial labeling was incorrect if the rule-based system provides inaccurate data, right?

00:08:58 — Customer 2: Wait, could someone explain this to me as if I were an idiot? I am trying to understand it, but so far I cannot.

00:09:06 — Customer 2: So, we have a rule-based system, which is a strict algorithm—literally just an algorithm—and then we have ML. The ML model outputs a result for some pattern that the rule-based system could not find itself.

00:09:19 — Customer 2: Or is the rule-based system used only for checking? The rule-based system itself does not output anything—or rather, it does not check anything?

00:09:26 — Team Member 2: No, the rule-based system itself never outputs anything, roughly speaking…

00:09:29 — Customer 2: So it is used purely for checking?

00:09:32 — Team Member 2: Yes, yes.

00:09:34 — Customer 2: Okay, I understand. But wait, the data was initially labeled by the rule-based system. How can our ML model…

00:09:44 — Customer 2: As I understand it… Actually, no, I do not understand it. It would be better if you explained it to the others.

00:09:51 — Customer 2: If we originally relied on it, how can the ML model outperform the result of the rule-based system if it was initially trained on the results of that rule-based system?

00:10:04 — Customer 1: Did you have some other script that actually produced the results? Or how did it work in general? That is what we are trying to understand.

00:10:12 — Team Member 2: No, no, no. It is the same one.

00:10:15 — Customer 1: Then where did the data come from if the rule-based system is used purely for checking? If the rule-based system does not produce results itself, where did the results for training the ML model come from?

00:10:27 — Team Member 2: Yes, they also came from the rule-based system.

00:10:31 — Team Member 2: Well, essentially, regarding the ML model, it is clear that our ML model is not completely accurate.

00:10:38 — Customer 1: What?

00:10:39 — Team Member 2: Our ML model…

00:10:42 — Team Member 2: Yes, I thought you were listening to me. Hello?

00:10:50 — Team Member 2: Hello?

00:10:51 — Customer 1: Hello.

00:10:52 — Customer 2: Yes, yes, yes.

00:10:54 — Customer 1: Now we can hear you.

00:10:55 — Team Member 2: I was saying that our ML model is not completely accurate, and the algorithm may…

00:11:04 — Team Member 2: On the other hand, yes, of course, it is also somewhat strange that I chose this kind of system. I wanted to add visualization as well, but we could have simply left it without any visualization and used only the result produced by the ML model.

00:11:31 — Team Member 2: When the ML model produces a result, the recognized pattern is shown. However, I trained the ML model so that it returns the pattern itself, but it does not return the exact vertices that were found or the specific candles.

00:11:48 — Customer 1: Why do we need the visualization? Everything is already visualized on the frontend.

00:11:58 — Team Member 2: No, there is no visualization of the actual pattern, meaning there are no lines drawn for the pattern. Without the rule-based system…

00:12:05 — Customer 1: I remember that we simply display the boundaries.

00:12:09 — Team Member 2: Yes, yes, yes.

00:12:13 — Team Member 2: That is what it is used for.

00:12:16 — Customer 2: But that is literally just feeding X into the ML model and getting Y. Those are the boundaries. Or what are you talking about, Vanya? I do not understand something.

00:12:33 — Team Member 2: Roughly speaking, we could say that we do not really have a complete ML system and that it currently works more in an experimental format.

00:12:43 — Customer 1: How does it work at all? What exactly do you mean by the ML model? Please explain it then.

00:12:51 — Team Member 2: In general, a pattern is constructed based on 96 candles.

00:12:58 — Team Member 2: We divided the chart into windows of 96 closed candles. Then the rule-based system labeled all of them, meaning that it found certain patterns in some of the windows.

00:13:11 — Team Member 2: For each window, the trend, volatility, various points, compression, and other features were calculated. In other words, the metrics that we calculate were recorded.

00:13:26 — Team Member 2: Then, as far as I understand, the number of examples for different patterns was balanced.

00:13:34 — Team Member 2: The older examples were used for training, while the newer examples were used for testing. After that, a LightGBM model was trained.

00:13:50 — Team Member 2: The model receives 96 candles, calculates all the features and metrics, uses them, and outputs a pattern with a certain probability.

00:14:03 — Team Member 2: Then the rule-based system validates all of that, roughly speaking. In fact, our ML model is trained on the rule-based results, and then the rule-based system validates it.

00:14:16 — Customer 1: In general, it really is… It is simply unclear how the situation occurs where the ML model outputs something, but we do not display it on the frontend because the rule-based system did not validate it.

00:14:28 — Customer 1: Why would we need to display it? Vanya said that something had been fixed. I understood it as the ML model producing something, but because of the rule-based system, it was not shown on the frontend.

00:14:42 — Customer 1: Why would we display it then if we validate it using the rule-based system? What exactly was the situation? What was the use case?

00:14:51 — Team Member 2: The situation was, for example, that the system displayed a triangle, but there were no lines on the chart at all.

00:15:01 — Customer 1: Where was the triangle displayed?

00:15:04 — Team Member 2: What?

00:15:05 — Customer 1: The triangle?

00:15:07 — Team Member 2: In the ML panel, it says either “no reliable pattern” or displays a certain pattern.

00:15:13 — Team Member 2: There were cases where the panel said that there was, for example, a triangle pattern and displayed some of its indicators, but nothing appeared on the chart.

00:15:22 — Customer 1: So was it some kind of frontend display problem? Or what exactly was it?

00:15:28 — Team Member 2: No, the problem was specifically that the ML model recognized a pattern, but the rule-based system filtered it out.

00:15:36 — Customer 1: So it was validated by the rule-based system when it was displayed?

00:15:40 — Team Member 2: Exactly.

00:16:07 — Customer 1: Why?

00:16:09 — Team Member 2: Well, probably because… I do not know why.

00:16:15 — Customer 1: It is just that the panel displays something like “triangle,” but where that triangle is located is unclear.

00:16:23 — Customer 1: That triangle is essentially unconfirmed because the rule-based system did not detect it.

00:16:35 — Customer 1: It is much better to display nothing at all and say that there is no pattern than to display an unreliable pattern.

00:16:42 — Team Member 2: That is how it works now.

00:16:44 — Customer 1: But you said that it would be displayed the other way around.

00:16:46 — Team Member 2: No, no, no.

00:16:48 — Customer 1: Then I do not understand what the problem was.

00:16:51 — Team Member 2: Let me explain it again.

00:16:53 — Team Member 2: The ML model… I am trying to explain the process again. The ML model recognized a certain pattern.

00:17:01 — Customer 1: I understand. Let us keep it abstract.

00:17:06 — Team Member 2: There are 96 candles. Then, in parallel, the rule-based system also recognizes a pattern.

00:17:14 — Team Member 2: Both systems return JSON containing a parameter called label.

00:17:23 — Team Member 2: It is essentially the name of the pattern. If the labels do not match, it means that the pattern was not confirmed, and nothing is displayed. That 
is how it works now.

00:17:34 — Team Member 2: Previously, this check did not exist. For example, the rule-based system did not recognize the pattern, so the lines were not drawn.

00:17:44 — Team Member 2: However, the ML model recognized it, and the panel displayed a message saying that a particular pattern had been detected.

00:17:50 — Customer 1: Was that how it worked before, or is that how it works now?

00:17:53 — Team Member 2: That was how it worked before.

00:17:56 — Customer 1: So previously it was not validated by the rule-based system?

00:18:01 — Team Member 2: No. I think I simply explained it differently at first.

00:18:05 — Customer 1: I remember that during the previous meeting we discussed this, and you definitely said that it was validated.

00:18:11 — Team Member 2: Maybe it was not. Maybe it was validated.

00:18:22 — Team Member 2: Anyway, that is not important.

00:18:27 — Customer 1: What metrics does the model currently have? And how many cases are filtered out by the rule-based system?

00:18:35 — Team Member 2: Metrics of the ML model?

00:18:37 — Customer 1: Yes.

00:18:39 — Team Member 2: What exactly do you mean by metrics?

00:18:42 — Customer 2: Yes, I do not fully understand either. Do you mean the data that the model receives?

00:18:58 — Customer 1: No, no, no.

00:19:04 — Customer 1: I mean metrics such as model quality and so on.

00:19:08 — Team Member 2: Yes, yes, yes.

00:19:10 — Customer 2: Maybe recall and precision as well.

00:19:16 — Team Member 2: The accuracy was approximately 0.7.

00:19:21 — Team Member 2: As far as I understand, we have six metrics. The first is accuracy, which is the proportion of correct answers.

00:19:29 — Team Member 2: Then there is precision, which shows how accurate the predictions of a particular pattern are.

00:19:35 — Team Member 2: Recall shows what proportion of the real patterns the model detected.

00:19:40 — Team Member 2: The F1-score represents the balance between precision and recall for each class.

00:19:47 — Team Member 2: Macro F1 is the average F1-score across all patterns without giving priority to the larger classes.

00:19:55 — Team Member 2: The confusion matrix shows which patterns the model confuses with each other.

00:20:01 — Customer 1: Yes, yes.

00:20:02 — Customer 1: What are the actual values?

00:20:04 — Team Member 2: Oh, the values for the metrics?

00:20:06 — Customer 1: Yes, yes.

00:20:08 — Team Member 2: I do not know.

00:20:09 — Team Member 2: I remember that it was approximately…

00:20:11 — Customer 1: It would be better to know the exact values.

00:20:14 — Team Member 2: We can check and calculate them now. They should be in a table.

00:20:24 — Customer 1: Ivan, do it.

00:20:27 — Team Member 2: It is in the ...ipynb file. I did not calculate it manually like that.

00:20:35 — Customer 1: Let us write something so that it simply calculates the metrics.

00:20:40 — Customer 1: Please share your screen.

00:20:43 — Team Member 2: I am already working on it.

00:20:56 — Customer 2: Do you know where your training scripts and the model itself are located?

00:21:03 — Team Member 2: We have a folder there. The rule-based recording…

00:21:08 — Customer 2: Which folder? What?

00:21:10 — Customer 1: Could you send a link to the Git repository here in the chat? Telegram is not working.

00:21:14 — Team Member 2: The metrics are located in… Should I send you the file or a GitHub link?

00:21:20 — Customer 1: What kind of file is it?

00:21:22 — Team Member 2: There is a file in our GitHub repository, roughly speaking.

00:21:27 — Customer 1: Okay, send it.

00:21:28 — Customer 2: Let us simply open that notebook, the .ipynb file or whatever it is called.

00:21:32 — Customer 2: And calculate it there. We can ask GPT to…

00:21:37 — Team Member 2: I have already asked it.

00:21:39 — Customer 1: Could you show it to us?

00:21:41 — Team Member 2: Yes, yes, yes, yes. I am starting the screen sharing now. Here it is.

00:21:49 — Team Member 2: Here, each folder contains statistics for each timeframe, as far as I understand.

00:21:57 — Customer 1: What is in there?

00:22:00 — Team Member 2: There is a matrix.json file here. It contains the relevant information.

00:22:08 — Customer 1: I do not see accuracy here.

00:22:11 — Team Member 2: It is the very first value.

00:22:13 — Customer 1: This is the previous model, not the current one.

00:22:15 — Team Member 2: Or is it… LightGBM.

00:22:18 — Customer 1: LightGBM, yes. Or do we have another model?

00:22:21 — Team Member 2: No, this is the correct one.

00:22:24 — Customer 1: For some reason, there was another model there. The baseline model.

00:22:29 — Team Member 2: Anyway, for example, the accuracy for one-minute candles is 0.75.

00:22:36 — Customer 1: Oh, here it is. This is calculated relative to the rule-based results, correct?

00:22:45 — Team Member 2: Yes, yes. Look.

00:22:48 — Customer 1: So our pattern recognition accuracy relative to the rule-based results is 75%.

00:22:54 — Team Member 2: Yes, that is correct. The macro F1-score is 0.76.

00:23:01 — Team Member 2: There are also per-class values there, with recall and precision listed below.

00:23:09 — Customer 1: Yes, I can see it. It is listed for double bottom, double top, flag, and head and shoulders.

00:23:17 — Customer 1: What is the accuracy?

00:23:20 — Team Member 2: As far as I understand, accuracy is calculated separately for each timeframe.

00:23:26 — Customer 1: And precision… It seems that it should be calculated separately for each pattern.


00:23:31 — Customer 2: Right.

00:23:32 — Customer 1: Is precision not included in accuracy? Are they not the same thing?

00:23:36 — Team Member 2: No, they are different, different, different. Precision shows how accurate the predictions for a particular pattern are, while accuracy is the proportion of all correct answers.

00:23:48 — Customer 1: Could you quickly add a feature so that the website has some kind of switch?

00:23:55 — Team Member 1: I can add it to the same tab where the scripts will be located.

00:24:02 — Customer 1: No, I mean a switch that would allow the pattern to be detected either by the ML model or by the rule-based system.

00:24:11 — Team Member 1: Oh, I understand. Yes, I think we can do that.

00:24:18 — Customer 1: Yes, let us quickly implement it. Since everything has already been written, and you only need to feed the candles into it and obtain the result, it 
should not be difficult.

00:24:26 — Team Member 1: Yes, yes.

00:24:28 — Customer 1: Let us do it that way, then.

00:24:31 — Customer 1: Okay. By the way, you also mentioned Mongo.

00:24:36 — Customer 1: Was it already there before, or not? I thought that only PostgreSQL was used.

00:24:42 — Team Member 1: The databases?

00:24:43 — Customer 1: Yes, the databases.

00:24:45 — Team Member 1: We did not mention Mongo. We talked about TimescaleDB and PostgreSQL.

00:24:50 — Customer 1: All right, okay, okay.

00:24:53 — Customer 1: Understood. I probably do not have any more questions overall.

00:24:58 — Customer 1: I would like to see this switch, and that is probably all.

00:25:06 — Customer 1: What about Docker Compose? What questions did you have about it, Andrey?

00:25:12 — Customer 2: You moved the database and the other services into separate containers, correct?

00:25:18 — Team Member 1: Everything is assembled into one large container, and that container consists of smaller ones. There is the frontend, backend, and database.

00:25:24 — Customer 2: No, no, stop, stop, stop.

00:25:27 — Customer 2: It is not one large container. It is some kind of combined setup. You still have several containers.

00:25:34 — Customer 1: Yes, yes, yes. If it were one large container, it would be Kubernetes. You most likely do not have that.

00:25:41 — Team Member 1: No, no, no. It would be more correct to call it a group of containers.

00:25:46 — Customer 2: In any case, you have a separate container—or rather, a separate image—for the backend, frontend, PostgreSQL, TimescaleDB, and that is all.

00:25:54 — Team Member 1: Yes, yes. There is also Grafana for visualization.

00:25:59 — Customer 2: Yes, yes.

00:26:03 — Team Member 1: All the variables are included in the .env file. There is also a .env.example file.

00:26:09 — Team Member 1: I have almost moved everything there, as you requested.

00:26:13 — Customer 1: Excellent.

00:26:14 — Team Member 1: Right.

00:26:16 — Team Member 1: We will now work on finishing the switches that you requested.

00:26:21 — Team Member 1: I will finish the scripts so that you can also launch all the scripts we have directly from the website. They may be useful to you.

00:26:31 — Customer 1: Uh-huh. Okay.

00:26:34 — Customer 1: So, did you generally enjoy working on the project?

00:26:39 — Team Member 3: Yes, it was a lot of fun.

00:26:41 — Customer 1: Was it useful?

00:26:43 — Team Member 3: Yes, yes. But it turned out to be more difficult because there were more details involved.

00:26:49 — Team Member 3: I liked it compared with something like a toolkit course.

00:26:55 — Team Member 3: We had certain tasks there, but in practice nobody used the solutions to those tasks.

00:27:02 — Team Member 3: Here, it is nice that you have a real task, you solve it, and afterward you can actually use the result and look at it.

00:27:10 — Team Member 3: You have your own website, roughly speaking, with a chart and everything else.

00:27:15 — Team Member 3: You understand where everything comes from and how everything works. It is genuinely interesting.

00:27:22 — Customer 1: Excellent.

00:27:24 — Team Member 3: There was also useful experience in communicating with the team.

00:27:29 — Customer 1: How was the communication within your team?

00:27:33 — Team Member 3: Our team is extremely friendly.

00:27:35 — Customer 1: What?

00:27:36 — Customer 2: “Friend”?

00:27:37 — Team Member 3: Friendly, friendly.

00:27:38 — Customer 1: Oh, friendly.

00:27:40 — Team Member 3: We even had team-building activities a couple of times.

00:27:43 — Customer 1: Will the female members of the team say anything today? It would also be interesting to hear from them.

00:27:51 — Team Member 3: The girls are just shy.

00:27:55 — Team Member 4: I think I can say something.

00:27:57 — Customer 1: Maybe you are deceiving us now and things are actually different?

00:28:01 — Customer 2: Yes, perhaps you are holding their phones hostage.

00:28:04 — Team Member 3: No, no, no. We respect and appreciate the girls.

00:28:09 — Customer 1: By the way, one more question. Please send me the repository link.

00:28:15 — Customer 1: Or… I wanted to check the README. Does it contain everything?

00:28:21 — Team Member 1: I sent it.

00:28:23 — Customer 1: Where? Here?

00:28:25 — Team Member 1: Yes, directly here.

00:28:27 — Customer 1: For some reason, I do not have access to the chat.

00:28:36 — Customer 1: Could you send it again in the Telegram chat, please?

00:28:39 — Team Member 1: Yes, one moment.

00:28:40 — Customer 1: Oh, no, I found it.

00:28:43 — Customer 2: Damn, I still have not found yours.

00:28:49 — Customer 1: Yes, thank you.

00:28:52 — Customer 1: Did it work? Was it sent?

00:28:55 — Team Member 1: It was sent, it was sent.

00:29:07 — Customer 1: The README contains instructions explaining how to run everything, correct? Are those instructions up to date?

00:29:14 — Team Member 1: Yes, yes, yes. Roughly speaking, you need to copy the .env file, fill in all the required values, and start everything.

00:29:24 — Customer 1: All right, everything is fine.

00:29:29 — Team Member 1: The scripts are also documented there, particularly the script for loading old candles. Everything is described in detail.

00:29:40 — Customer 1: Okay. I do not have any more questions overall.

00:29:45 — Customer 2: Neither do I.

00:29:48 — Customer 1: Thank you for developing the project. I hope that the experience was genuinely useful for you.

00:29:54 — Customer 1: Should you have any ideas in the future, feel free to come back to us.

00:29:58 — Team Member 1: Thank you.
