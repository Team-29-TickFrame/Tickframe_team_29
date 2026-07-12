# Sprint Review Transcript
## Part1:
00:00:00 – Customer 1: How are things going? How is the progress?
00:00:06 – Team Member 1: Things are moving forward. I’ve been working on the UI and dashboard customization so users can move widgets around, resize windows, and improve usability. Ivan has been actively working on the ML component.
00:00:20 – Customer 1: Great. What is the current state of the ML component?
00:00:25 – Team Member 1: Ivan can explain it in detail, but first I can show the current implementation.
00:00:35 – Team Member 1: Here is the current interface. The system is already detecting some patterns. For example, it currently identifies a triangle pattern. Sometimes it draws pattern lines on the chart, although the visualization is still inconsistent.
00:01:24 – Customer 1: How can users understand where exactly the pattern was detected?
00:01:29 – Team Member 1: That is one of the improvements we are currently working on. We plan to continuously calculate patterns and provide a dedicated menu where users can manage and inspect detected patterns.
00:02:05 – Customer 1: Last week we agreed that pattern visualizations would be prepared in Figma.
00:02:12 – Team Member 1: We do not have the Figma mockups yet, but we already have a working prototype implementation.
00:02:29 – Team Member 1: Ivan, please explain the pattern detection system.
00:02:40 – Team Member 2: At the moment we support several patterns: Double Top, Double Bottom, Triangle, Head and Shoulders, and Flag. The Flag visualization is not always displayed correctly because there is not always enough data available to draw it properly.
00:03:40 – Team Member 2: For Double Top and Double Bottom we draw the levels corresponding to the two peaks or bottoms, along with the neckline level.
00:04:50 – Customer 1: What is the accuracy of the model?
00:05:10 – Team Member 2: During training we achieved approximately 70% accuracy on one-minute data and around 60% on some other datasets.
00:06:08 – Customer 1: Can you explain the dataset used for training?
00:06:13 – Team Member 2: We used one-minute Binance candle data. We also implemented a rule-based detector that identifies patterns according to predefined rules. The ML model then learns from those detections.
00:07:00 – Team Member 2: Currently the ML model first predicts a pattern and then the result is validated using the rule-based detector.
00:07:34 – Team Member 2: If the ML prediction and the rule-based detector disagree, the pattern lines are not drawn on the chart.
00:08:10 – Customer 1: Did you develop the rule-based detector yourselves?
00:08:14 – Team Member 2: No. The implementation was generated with assistance from an AI coding tool.
00:08:48 – Customer 1: So the AI-generated detector was used to label the dataset, and then the model was trained on those labels?
00:08:55 – Team Member 2: Yes, that is correct.
00:09:02 – Customer 1: Did you manually verify that the generated labels were actually correct? I am not entirely convinced this approach is reliable.
00:09:30 – Customer 1: So there was no manual annotation and no externally labeled dataset?
00:09:36 – Team Member 2: Correct. We used market data, but the labels came from the rule-based detector.
00:10:31 – Customer 1: Which system is considered the primary source of truth: the ML model or the rule-based detector?
00:10:50 – Team Member 2: The ML model is the main detection mechanism, but we currently require confirmation from the rule-based detector before displaying the result.
00:11:13 – Customer 1: Then effectively the rule-based detector becomes the master system.
00:11:21 – Team Member 2: At the moment, yes. This was done because earlier confidence thresholds were too strict and almost all results were classified as “No Reliable Pattern”.
00:12:33 – Customer 1: Does that mean the displayed pattern accuracy is currently around 50%?
00:12:38 – Team Member 2: No. The threshold only determines whether a pattern is displayed. It is not the same thing as model accuracy.
00:14:10 – Customer 1: Why did you choose this specific model instead of another approach?
00:14:16 – Team Member 2: Initially I used a Gaussian classifier, but its performance was significantly worse for this task. Later I switched to LightGBM.
00:15:24 – Customer 1: How exactly was the model trained?
00:15:31 – Team Member 2: We replaced the original synthetic dataset with Binance market data and retrained the model using labels produced by the rule-based detector.
00:16:07 – Customer 1: Was the rule-based detector validated independently?
00:16:16 – Customer 1: I generally do not trust AI-generated code without verification, so I would like to understand how it was tested.
00:17:16 – Customer 1: Right now it sounds like the entire pattern detection process depends on AI-generated code.
00:17:30 – Customer 1: Did you investigate any existing solutions or pretrained models?
00:17:58 – Team Member 2: No, we did not use existing pretrained models.
00:18:18 – Customer 1: Why did you choose this approach?
00:18:22 – Team Member 2: We could not find a sufficiently large labeled dataset with the patterns we needed, so we decided to build the solution ourselves.
00:18:48 – Customer 2: I think the question is more about the choice of model. Why was this particular model selected?
00:19:03 – Team Member 2: It is a machine learning model suitable for structured tabular data. We evaluated several alternatives and this one produced the best results.
00:19:43 – Team Member 2: During development we also experimented with various AI tools, including GPT and other popular models, mainly for assistance and prototy

## Part2:
00:00:00 – Customer 1: The mouse disconnected. Alright. Also, could you please send us later a list of who worked on what during the project? You will need it soon for the final report.
00:00:07 – Customer 1: Not just something like backend, ML, frontend, and so on, but specifically which functionality each person worked on.
00:00:10 – Team Member 1: Yes, we can do that. Roughly speaking, the girls were mostly working on documentation and similar tasks, while the actual code was mainly developed by Ivan and me.
00:00:55 – Customer 1: Put it in a table or a document.
00:00:57 – Team Member 1: Okay, sure.
00:00:58 – Team Member 1: Can you hear me now? My laptop internet keeps disconnecting.
00:01:04 – Customer 1: Yes, yes, we can hear you.
00:01:07 – Customer 1: So, Ivan, what was the question again? Why did you decide to use the model you mentioned? Did you consider using GPT, LLaMA, or something similar? Why was this model chosen? I simply haven't heard of it before, so I'm curious.
00:01:20 – Team Member 2 (Ivan): Well, considering the amount of time we had left, and since this is actually my first time working with machine learning, I did some research and chose this model because it seemed suitable for the task.
00:01:32 – Customer 1: Where exactly did you research it?
00:01:33 – Team Member 2 (Ivan): Well, I talked to people, looked things up, checked GPT, searched online.
00:01:38 – Customer 1: There is no right or wrong answer here. I'm just interested in where the information came from.
00:02:56 – Customer 1: Hello?
00:02:57 – Team Member 2 (Ivan): Hello, yes.
00:02:58 – Customer 1: Did you hear what I said?
00:03:00 – Team Member 2 (Ivan): I’m not sure what part you heard. I said that I chose this model because it’s my first time working with machine learning. First I researched different options and tried to understand what would be suitable as a starting point.
00:03:18 – Customer 1: Just from the Internet?
00:03:20 – Team Member 2 (Ivan): Yes, from the Internet.
00:03:22 – Customer 1: Got it. Then should we look at the rule-based detector?
00:03:27 – Team Member 1: Let me reconnect first because everything disconnected on my side.
00:03:56 – Customer 1: Maybe I can share my screen and you can tell us where it is located in the repository so we can look at it.
00:04:01 – Team Member 2 (Ivan): Sure.
00:04:03 – Customer 1: Ivan, can you send the repository link in the chat?
00:04:05 – Team Member 2 (Ivan): Yes, I'll send it now.
00:04:52 – Customer 1: Is everything pushed to GitHub?
00:04:54 – Team Member 2 (Ivan): Yes, everything is pushed.
00:04:57 – Customer 1: Which repository is it in? The main shared repository?
00:05:12 – Team Member 1: Yes, everything is there in my repository.
00:05:14 – Customer 1: Roma, can you share the screen?
00:05:15 – Team Member 1: Yes, I’m just trying to find where it is located.
00:05:20 – Team Member 1: Maybe here? I can see LightGBM and realdata.
00:05:24 – Team Member 1: Ivan, where is it located?
00:05:26 – Team Member 2 (Ivan): Check dataset.py. I think it is there. The previous version was there.
00:05:12 – Team Member 1: Yes, yes, everything is there in my repository.
00:05:13 – Customer 1: Roma, can you show the screen?
00:05:14 – Team Member 1: Yes, yes, yes. I’m just trying to find where it is located.
00:05:20 – Team Member 1: Maybe here? Here is LightGBM, realdata.
00:05:23 – Team Member 1: Where is it located, Ivan?
00:05:24 – Team Member 2 (Ivan): Check dataset.py, most likely. Dataset.py, most likely. The previous version was there.
00:06:03 – Team Member 1: Where? I don’t understand. Is it somewhere here?
00:06:06 – Team Member 2 (Ivan): No, in ML, in ML. That is LightGBM itself.
00:06:22 – Customer 1: Okay, this part is not very interesting. What exactly is this? I don’t really understand.
00:06:28 – Team Member 1: The classes and labels are defined here.
00:06:41 – Team Member 1: Well, here it takes the dataset.
00:06:44 – Customer 1: And then what?
00:06:45 – Team Member 1: “If label not in payload.” Payload is the uploaded JSON. Like this.
00:07:01 – Customer 1: It seems like the labels are stored in the dataset or something. Ivan, where is that rule-based thing located? The thing that validates whether there is a pattern or not.
00:07:13 – Customer 1: And what are these metrics? Where is the rule-based part? Ivan, where is it? I thought it was in the dataset, but I don’t remember.
00:08:00 – Customer 1: I still don’t understand how it currently works. You said that when a pattern is displayed, it is checked against this rule-based detector to confirm that the pattern actually exists.
00:08:12 – Customer 1: Where exactly does that happen?
00:08:14 – Customer 1: Roma, scroll back a little.
00:08:25 – Team Member 1: Okay.
00:08:26 – Customer 1: Let’s open the backend. Do you have a separate backend wrapper around the ML part?
00:08:31 – Customer 1: Or not? How does the interaction with the ML component actually work?
00:08:35 – Team Member 1: I have no idea.
00:08:36 – Customer 1: What is inside init.py?
00:08:39 – Team Member 1: Init.py?
00:08:40 – Customer 1: Yes, the file currently on the screen.
00:09:01 – Customer 1: Alright. Look, when pattern recognition happens, a request is sent from the frontend to the backend, right?
00:09:08 – Team Member 1: Yes, yes.
00:09:09 – Customer 1: Okay.
00:09:10 – Team Member 1: I think I found the rule-based component now.
00:09:29 – Team Member 1: Hopefully everyone can see it.
00:09:31 – Team Member 1: As far as I understand, this is the rule-based component.
00:09:35 – Customer 1: Ivan, how does it work? Let’s start from the very beginning.
00:10:08 – Customer 1: Alright, class-based thresholds.
00:10:11 – Customer 1: Okay.
00:10:12 – Customer 1: What else is interesting here?
00:10:15 – Customer 1: Alright.
00:10:16 – Customer 1: So, threshold, prediction, label, prediction.
00:11:11 – Customer 1: What exactly is prediction?
00:11:14 – Customer 1: Ah, I see.
00:11:16 – Customer 1: So the model is first trained through this rule-based system.
00:11:21 – Customer 1: And then the output is passed through the rule-based detector again.
00:11:38 – Customer 1: Alright, give me a second.
00:11:40 – Customer 1: The problem with this approach is that the model cannot really move beyond the boundaries defined by the rule-based system.
00:11:49 – Customer 1: If there is some unusual market movement or a significant change, it may simply fail to recognize the pattern.
00:12:03 – Customer 1: If, for example, there is a sudden spike or something changes dramatically, it will not detect that pattern.
00:12:09 – Team Member 2 (Ivan): That sounds logical.
00:12:14 – Customer 1: In practice, it is mostly imitating similarity.
00:12:18 – Customer 1: Well, at this point there is probably no reason to change everything.
00:12:22 – Customer 1: There is very little time left.
00:12:29 – Team Member 1: Why not? We could still try something. I could help and maybe we can improve it.
00:12:36 – Customer 1: The issue is that you have already chosen this approach and built the whole pipeline around it.
00:12:43 – Customer 1: You can still experiment if everything else is already finished.
00:12:50 – Customer 1: I would recommend manually checking the results as well.
00:12:55 – Customer 1: Don’t rely solely on the rule-based checker.
00:12:58 – Customer 1: Look at the detected patterns yourselves and try to determine whether they actually make sense.
00:13:14 – Customer 1: Alright, let’s stop discussing the ML part for today.
00:13:18 – Customer 1: We are all getting a bit overwhelmed already.
00:13:21 – Customer 1: Let’s talk about deployment instead.
00:13:24 – Customer 1: Is the product currently deployed somewhere, or does it only run locally?
00:13:29 – Team Member 1: It is deployed on an Innopolis University VM.
00:13:35 – Customer 1: Is that the latest version?
00:13:37 – Team Member 1: Yes, yes, it is the latest version.
00:13:39 – Team Member 1: There are a couple of small patches that I only applied locally, but they are mostly content-related and do not affect functionality.
00:13:49 – Customer 1: Okay, good.
00:13:52 – Customer 1: Next question.
00:13:54 – Customer 1: If we, as customers, want to deploy the project ourselves, are all instructions available in the repository?
00:14:01 – Team Member 1: Yes, all instructions are included.
00:14:03 – Team Member 1: Everything is assembled into a single Docker-based deployment.
00:14:07 – Customer 1: Great, excellent.
00:14:09 – Customer 1: What about the database?
00:14:11 – Customer 1: How are you using it?
00:14:12 – Customer 1: What database do you use and where is it stored?
00:14:15 – Team Member 1: We use PostgreSQL.
00:14:18 – Customer 1: Okay.
00:14:19 – Customer 1: PostgreSQL.
00:14:20 – Customer 1: How is it started?
00:14:22 – Team Member 1: Through Docker as well.
00:14:37 – Customer 1: I don’t actually see PostgreSQL in the compose configuration.
00:14:41 – Customer 1: Do you use TimescaleDB?
00:14:43 – Team Member 1: Yes, TimescaleDB is there.
00:14:45 – Customer 1: So it runs inside a container?
00:14:47 – Team Member 1: Yes, yes, exactly.
00:14:54 – Customer 1: Okay, okay.
00:14:56 – Customer 1: And environment variables are also used?
00:14:59 – Customer 1: Configuration through ENV variables, I mean.
00:15:08 – Team Member 1: Yes, there are shared configuration settings.
00:15:08 – Team Member 1: There are shared settings there. For example, if some WebSocket connection fails, the configuration can be changed immediately and so on.
00:15:20 – Customer 1: Good.
00:15:21 – Team Member 1: Things like route rates and so on are configured there as well, so the ENV file is fairly extensive.
00:15:36 – Customer 1: Please move the port configuration into ENV variables as well.
00:15:40 – Customer 1: I can see Grafana and Prometheus there, but for example the backend ports and PostgreSQL ports should also be configurable.
00:15:47 – Customer 1: Those should be moved there too.
00:15:49 – Team Member 1: Okay, okay.
00:15:50 – Customer 1: Roma, can you check whether the recording is still running? I can’t see it from my phone.
00:15:58 – Team Member 1: No.
00:16:00 – Team Member 1: Apparently it...
00:16:02 – Team Member 1: Well, in general, I don’t think we lost much.
00:16:05 – Team Member 1: The recording was running before. I saw the indicator blinking.
00:16:13 – Team Member 1: It probably stopped when...
00:16:15 – Team Member 1: Ah, no, it was recording. Yes, it was recording.
00:16:17 – Team Member 1: Yes, it definitely was.
00:16:18 – Customer 1: Can you turn it back on now, Roma?
00:16:20 – Team Member 1: Well, there is probably no point now.
00:16:22 – Customer 1: Yes, we are basically finishing anyway.
00:16:26 – Customer 1: If you still have any questions, you can turn it on so that they are recorded.
00:16:31 – Team Member 1: How exactly should we hand everything over to you?
00:16:35 – Team Member 1: Do we simply give you the repository and that’s it, or how should the process work?
00:16:40 – Customer 1: You will give us the repository.
00:16:42 – Customer 1: Well, actually, you have already given it to us.
00:16:44 – Customer 1: From that point, we will handle everything ourselves.
00:16:47 – Team Member 1: What about repository permissions or anything else?
00:16:50 – Customer 1: No, there is no point in that anymore.
00:16:53 – Customer 1: We will simply clone the repository and that will be enough.
00:16:57 – Team Member 1: Got it.
00:16:58 – Customer 1: Product support is not really expected.
00:17:01 – Customer 1: This is more like a custom development project.
00:17:04 – Customer 1: You deliver it, we accept it, and that’s it.
00:17:08 – Customer 1: In general, we don’t have any more questions.
00:17:11 – Customer 1: We should still have one more call together, which will likely be the final one.
00:17:15 – Team Member 1: Okay.
00:17:16 – Customer 1: We will see what the final result looks like.
00:17:20 – Customer 1: And that will probably conclude everything.
00:17:22 – Customer 1: Do you have any questions about the current state of the project or the final week?
00:17:28 – Team Member 1: Is there anything else we should do besides what has already been discussed?
00:17:33 – Customer 1: Take another look at the model and see whether you can improve its accuracy.
00:17:42 – Customer 1: And in general, maybe you will still have time to quickly rebuild or improve something if necessary.
00:17:48 – Team Member 1: Okay.
00:17:50 – Customer 1: If it doesn’t work out, don’t delete the current implementation.
00:17:54 – Customer 1: Make sure the working version remains intact.
00:17:56 – Customer 1: You can make it a separate mode if you want.
00:18:00 – Customer 1: Another team working on a similar project is complaining that labeling data is very difficult.
00:18:06 – Customer 1: There are too few people, too little time, and not enough resources.
00:18:10 – Team Member 2 (Ivan): That is exactly why we used the rule-based approach.
00:18:14 – Team Member 2 (Ivan): I looked into graphical annotations and similar solutions, but there really weren’t any available.
00:18:21 – Team Member 2 (Ivan): So we decided to go with this approach.
00:18:25 – Team Member 2 (Ivan): Because if you want a proper dataset, you need a large number of examples.
00:18:31 – Team Member 2 (Ivan): That was my reasoning.
00:18:42 – Customer 1: Alright, alright, sounds good.
00:18:44 – Customer 1: Then that’s everything.
00:18:46 – Customer 1: No more questions.
00:18:47 – Customer 1: We’re done.
00:18:49 – Team Member 1: I think so, yes.
00:18:52 – Customer 1: Just to summarize one last time.
00:18:55 – Customer 1: You need to send us a list of who worked on what.
00:18:59 – Customer 1: Move the ports into ENV variables.
00:19:02 – Customer 1: And, if possible, make some improvements to the ML component.
00:19:07 – Customer 1: That’s basically everything.
00:19:09 – Customer 1: Did I miss anything?
00:19:11 – Customer 2 (Nikolay): I don’t think so.
00:19:13 – Customer 1: Alright, good.
00:19:15 – Customer 1: Yes, that’s all.
00:19:18 – Customer 1: Thank you very much.
00:19:20 – Customer 1: Have a great day.
00:19:23 – Team Member 1: Same to you.
00:19:24 – Team Member 1: Thank you.
