-- ManoRakshak Database Dump
-- Generated via Python dumper script
CREATE DATABASE IF NOT EXISTS `manorakshak_db`;
USE `manorakshak_db`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `appointments`;
DROP TABLE IF EXISTS `assessments`;
DROP TABLE IF EXISTS `chat_messages`;
DROP TABLE IF EXISTS `chat_sessions`;
DROP TABLE IF EXISTS `diary_photos`;
DROP TABLE IF EXISTS `diary_tags`;
DROP TABLE IF EXISTS `game_progress`;
DROP TABLE IF EXISTS `journal_entries`;
DROP TABLE IF EXISTS `mood_entries`;
DROP TABLE IF EXISTS `therapists`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `wellness_scores`;

-- ------------------------------------------------------
-- Table structure for table `appointments`
-- ------------------------------------------------------
CREATE TABLE `appointments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `therapist_id` int(11) NOT NULL,
  `appointment_date` date NOT NULL,
  `appointment_time` varchar(50) NOT NULL,
  `status` varchar(50) DEFAULT 'Pending',
  `notes` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `therapist_id` (`therapist_id`),
  CONSTRAINT `appointments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `appointments_ibfk_2` FOREIGN KEY (`therapist_id`) REFERENCES `therapists` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table `appointments`
INSERT INTO `appointments` (`id`, `user_id`, `therapist_id`, `appointment_date`, `appointment_time`, `status`, `notes`, `created_at`) VALUES (1, 3, 7, '2026-06-18', '02:00 PM', 'Confirmed', 'i feel depressed', '2026-06-17T01:40:43');
INSERT INTO `appointments` (`id`, `user_id`, `therapist_id`, `appointment_date`, `appointment_time`, `status`, `notes`, `created_at`) VALUES (2, 8, 1, '2026-06-17', '10:00 AM', 'Pending', 'Struggling with stress.', '2026-06-17T01:54:49');
INSERT INTO `appointments` (`id`, `user_id`, `therapist_id`, `appointment_date`, `appointment_time`, `status`, `notes`, `created_at`) VALUES (3, 9, 7, '2026-06-19', '02:00 PM', 'Confirmed', 'i feel depressed', '2026-06-17T19:13:20');
INSERT INTO `appointments` (`id`, `user_id`, `therapist_id`, `appointment_date`, `appointment_time`, `status`, `notes`, `created_at`) VALUES (4, 11, 8, '2026-07-01', '10:00 AM', 'Confirmed', 'Feeling super integrated today.', '2026-06-17T22:58:34');
INSERT INTO `appointments` (`id`, `user_id`, `therapist_id`, `appointment_date`, `appointment_time`, `status`, `notes`, `created_at`) VALUES (5, 11, 8, '2026-07-01', '10:00 AM', 'Pending', 'Feeling super integrated today.', '2026-06-17T22:59:18');
INSERT INTO `appointments` (`id`, `user_id`, `therapist_id`, `appointment_date`, `appointment_time`, `status`, `notes`, `created_at`) VALUES (6, 11, 8, '2026-07-01', '10:00 AM', 'Confirmed', 'Feeling super integrated today 1781717431.9357827.', '2026-06-17T23:00:33');

-- ------------------------------------------------------
-- Table structure for table `assessments`
-- ------------------------------------------------------
CREATE TABLE `assessments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `type` varchar(20) NOT NULL,
  `score` int(11) NOT NULL,
  `severity` varchar(50) NOT NULL,
  `answers` text NOT NULL,
  `taken_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_assessment_user` (`user_id`),
  CONSTRAINT `fk_assessment_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `assessments`
INSERT INTO `assessments` (`id`, `user_id`, `type`, `score`, `severity`, `answers`, `taken_at`) VALUES (1, 13, 'PHQ9', 12, 'Moderate', '[3, 3, 2, 2, 1, 1, 0, 0, 0]', '2026-06-17T23:18:28');
INSERT INTO `assessments` (`id`, `user_id`, `type`, `score`, `severity`, `answers`, `taken_at`) VALUES (2, 13, 'GAD7', 6, 'Mild', '[1, 1, 1, 1, 1, 1, 0]', '2026-06-17T23:18:30');
INSERT INTO `assessments` (`id`, `user_id`, `type`, `score`, `severity`, `answers`, `taken_at`) VALUES (3, 3, 'PHQ9', 16, 'Moderately Severe', '[1, 1, 3, 1, 2, 2, 3, 2, 1]', '2026-06-17T23:20:27');
INSERT INTO `assessments` (`id`, `user_id`, `type`, `score`, `severity`, `answers`, `taken_at`) VALUES (4, 3, 'GAD7', 15, 'Severe', '[1, 2, 3, 2, 2, 2, 3]', '2026-06-17T23:23:05');
INSERT INTO `assessments` (`id`, `user_id`, `type`, `score`, `severity`, `answers`, `taken_at`) VALUES (5, 13, 'PHQ9', 27, 'Severe', '[3, 3, 3, 3, 3, 3, 3, 3, 3]', '2026-06-17T23:45:45');
INSERT INTO `assessments` (`id`, `user_id`, `type`, `score`, `severity`, `answers`, `taken_at`) VALUES (6, 13, 'GAD7', 21, 'Severe', '[3, 3, 3, 3, 3, 3, 3]', '2026-06-17T23:50:55');

-- ------------------------------------------------------
-- Table structure for table `chat_messages`
-- ------------------------------------------------------
CREATE TABLE `chat_messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `session_id` int(11) NOT NULL,
  `role` varchar(20) NOT NULL COMMENT 'user or assistant',
  `content` text NOT NULL,
  `is_crisis` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ix_chat_messages_id` (`id`),
  KEY `ix_msg_session` (`session_id`),
  CONSTRAINT `fk_msg_session` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=133 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `chat_messages`
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (1, 1, 'user', 'hello', 0, '2026-05-14T20:44:43');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (2, 1, 'assistant', 'Hello! I\'m glad you\'re here. How can I support you today?', 0, '2026-05-14T20:45:13');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (3, 36, 'user', 'i am not anxious', 0, '2026-06-18T13:38:54');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (4, 36, 'assistant', 'I\'m really glad to hear that you\'re not feeling anxious right now! 🌸 It\'s always great when things feel a bit lighter. What is on your mind today?', 0, '2026-06-18T13:38:55');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (5, 36, 'user', 'i am not anxious', 0, '2026-06-18T13:39:17');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (6, 36, 'assistant', 'I\'m really glad to hear that you\'re not feeling anxious right now! 🌸 It\'s always great when things feel a bit lighter. What is on your mind today?', 0, '2026-06-18T13:39:17');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (7, 36, 'user', 'hii', 0, '2026-06-18T13:39:19');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (8, 36, 'assistant', 'Hi there! Welcome back. This is a safe space for you. What\'s on your mind?', 0, '2026-06-18T13:39:19');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (9, 36, 'user', 'can you recommend a game to play?', 0, '2026-06-18T13:39:21');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (10, 36, 'assistant', 'I\'d love to suggest an activity for you! Based on your state, you might enjoy playing **Calm Grid Sudoku** 🔢.

*A soothing number puzzle designed to cultivate focus and clarity*.

It\'s a wonderful, mindful way to take a break and ground yourself. I\'ve placed a quick link below to play it! 🌿', 0, '2026-06-18T13:39:21');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (11, 36, 'user', 'summarize my diary', 0, '2026-06-18T13:39:23');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (12, 36, 'assistant', 'It looks like you haven\'t written any diary entries yet. 📖 You can write one on the Diary tab!', 0, '2026-06-18T13:39:23');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (13, 37, 'user', 'hello', 0, '2026-06-18T13:39:43');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (14, 37, 'assistant', 'Hello! I\'m really glad you\'re here. Whatever you\'re carrying right now, you don\'t have to carry it alone. How are you feeling today?

I noticed you logged a diary entry today feeling **Anxious** tagged with #work, #stress, #anxiety. How are you doing right now? I\'m here if you want to share or talk about it. 🌿', 0, '2026-06-18T13:39:43');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (15, 37, 'user', 'summarize my diary', 0, '2026-06-18T13:39:45');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (16, 37, 'assistant', 'Here is a summary of your latest diary entry from **2026-06-18** where you felt **Anxious**:

📖 *"I had a very stressful day at work. I feel completely overwhelmed and anxious about the upcoming deadlines."*

🏷️ **Tags**: #work, #stress, #anxiety

Writing is a powerful way to process experiences. Would you like to share more about how you\'re feeling right now?', 0, '2026-06-18T13:39:45');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (17, 38, 'user', 'Summarize my last diary entry', 0, '2026-06-18T13:42:16');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (18, 38, 'assistant', 'Here is a summary of your latest diary entry from **2026-06-17** where you felt **Joyful**:

📖 *""*

🏷️ **Tags**: None

Writing is a powerful way to process experiences. Would you like to share more about how you\'re feeling right now?', 0, '2026-06-18T13:42:16');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (19, 38, 'user', 'Give me some tips to feel better', 0, '2026-06-18T13:42:29');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (20, 38, 'user', 'How is my mood lately?', 0, '2026-06-18T13:42:51');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (21, 38, 'assistant', 'Here is what I see from your recent wellness metrics: 📊

• **Mood logs**: You\'ve written **7 diary entries** (streak: **0 days**). Your average logged mood is **Happy** (2.1/5).
• **Assessments**: Your latest self-assessment was **GAD7** with a score of **15** (**Severe** severity).

How are you feeling right now compared to these wellness trends?', 0, '2026-06-18T13:42:51');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (22, 38, 'user', 'Suggest a game', 0, '2026-06-18T13:43:04');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (23, 38, 'assistant', 'I\'d love to suggest an activity for you! Based on your state, you might enjoy playing **Color Your World** 🎨.

*Paint beautiful canvases to express and celebrate your positive mood*.

It\'s a wonderful, mindful way to take a break and ground yourself. I\'ve placed a quick link below to play it! 🌿', 0, '2026-06-18T13:43:04');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (24, 38, 'user', 'hii', 0, '2026-06-18T13:43:25');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (25, 38, 'assistant', 'Hello! I\'m really glad you\'re here. Whatever you\'re carrying right now, you don\'t have to carry it alone. How are you feeling today?', 0, '2026-06-18T13:43:25');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (26, 38, 'user', 'i feel alone', 0, '2026-06-18T13:43:33');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (27, 38, 'assistant', 'Thank you for sharing with me 🌿 I\'m here and I\'m listening. How can I support you today?', 0, '2026-06-18T13:43:46');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (28, 38, 'assistant', 'Thank you for sharing with me 🌿 I\'m here and I\'m listening. How can I support you today?', 0, '2026-06-18T13:43:46');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (29, 38, 'user', 'what just dont understand what i should do', 0, '2026-06-18T13:46:37');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (30, 38, 'assistant', 'Thank you for sharing with me 🌿 I\'m here and I\'m listening. How can I support you today?', 0, '2026-06-18T13:46:37');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (31, 38, 'user', 'you are not supporting', 0, '2026-06-18T13:46:50');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (32, 38, 'assistant', 'Thank you for sharing with me 🌿 I\'m here and I\'m listening. How can I support you today?', 0, '2026-06-18T13:46:50');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (33, 37, 'user', 'hello', 0, '2026-06-18T13:50:27');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (34, 37, 'assistant', 'Hello! I\'m really glad you\'re here. Whatever you\'re carrying right now, you don\'t have to carry it alone. How are you feeling today?

I noticed you logged a diary entry today feeling **Anxious** tagged with #work, #stress, #anxiety. How are you doing right now? I\'m here if you want to share or talk about it. 🌿', 0, '2026-06-18T13:50:27');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (35, 37, 'user', 'summarize my diary', 0, '2026-06-18T13:50:30');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (36, 37, 'assistant', 'Here is a summary of your latest diary entry from **2026-06-18** where you felt **Anxious**:

📖 *"I had a very stressful day at work. I feel completely overwhelmed and anxious about the upcoming deadlines."*

🏷️ **Tags**: #work, #stress, #anxiety

Writing is a powerful way to process experiences. Would you like to share more about how you\'re feeling right now?', 0, '2026-06-18T13:50:30');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (37, 38, 'user', 'hii', 0, '2026-06-18T13:52:07');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (38, 38, 'assistant', 'Hi there! Welcome back. This is a safe space for you. What\'s on your mind?', 0, '2026-06-18T13:52:07');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (39, 38, 'user', 'i feel lonely', 0, '2026-06-18T13:52:16');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (40, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿

🌴 *Tip: Sometimes a quiet distraction helps. Try escaping to the [Cozy Island Garden](/games/manorakshak_cozy_island_garden) activity.*', 0, '2026-06-18T13:52:35');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (41, 38, 'user', 'i am loosing my friends, they keep fighting with me all the time', 0, '2026-06-18T14:38:44');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (42, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T14:38:45');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (43, 38, 'user', 'hii', 0, '2026-06-18T14:42:39');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (44, 38, 'assistant', 'Hey! I\'m here and listening. How has your day been?', 0, '2026-06-18T14:42:39');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (45, 38, 'user', 'i feel lonely', 0, '2026-06-18T14:42:44');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (46, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿

🌴 *Tip: Sometimes a quiet distraction helps. Try escaping to the [Cozy Island Garden](/games/manorakshak_cozy_island_garden) activity.*', 0, '2026-06-18T14:42:45');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (47, 38, 'user', 'all my friend keep fighting with me , i feel so alone', 0, '2026-06-18T14:43:06');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (48, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿

🌴 *Tip: Sometimes a quiet distraction helps. Try escaping to the [Cozy Island Garden](/games/manorakshak_cozy_island_garden) activity.*', 0, '2026-06-18T14:43:06');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (49, 38, 'user', 'tell me what should i do when i have a fight with someone', 0, '2026-06-18T14:43:46');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (50, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T14:43:46');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (51, 38, 'user', 'hii', 0, '2026-06-18T14:58:54');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (52, 38, 'assistant', 'Hi there! Welcome back. This is a safe space for you. What\'s on your mind?', 0, '2026-06-18T14:58:54');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (53, 38, 'user', 'i feel great', 0, '2026-06-18T14:59:01');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (54, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T14:59:01');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (55, 38, 'user', 'i said i feel good', 0, '2026-06-18T14:59:10');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (56, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T14:59:10');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (57, 37, 'user', 'hello', 0, '2026-06-18T15:08:18');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (58, 37, 'assistant', 'Hey! I\'m here and listening. How has your day been?

I noticed you logged a diary entry today feeling **Anxious** tagged with #work, #stress, #anxiety. How are you doing right now? I\'m here if you want to share or talk about it. 🌿', 0, '2026-06-18T15:08:18');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (59, 37, 'user', 'summarize my diary', 0, '2026-06-18T15:08:20');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (60, 37, 'assistant', 'Here is a summary of your latest diary entry from **2026-06-18** where you felt **Anxious**:

📖 *"I had a very stressful day at work. I feel completely overwhelmed and anxious about the upcoming deadlines."*

🏷️ **Tags**: #work, #stress, #anxiety

Writing is a powerful way to process experiences. Would you like to share more about how you\'re feeling right now?', 0, '2026-06-18T15:08:20');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (61, 39, 'user', 'hello', 0, '2026-06-18T15:53:58');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (62, 39, 'assistant', 'Hello. This is a safe, non-judgmental space. What\'s going on for you today?', 0, '2026-06-18T15:53:58');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (63, 39, 'user', 'i am not anxious', 0, '2026-06-18T15:54:00');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (64, 39, 'assistant', 'That\'s wonderful! 🌿 What\'s been going well for you lately, or is there something you\'d like to explore?', 0, '2026-06-18T15:54:00');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (65, 39, 'user', 'what should i do when i fight with someone', 0, '2026-06-18T15:54:02');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (66, 39, 'assistant', 'For intrusive thoughts: don\'t try to force them away â€” that makes them louder. Try acknowledging them without engaging: \'I notice I\'m having the thought that...\' and let them pass like clouds.', 0, '2026-06-18T15:54:09');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (67, 39, 'user', 'suggest a game', 0, '2026-06-18T15:54:11');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (68, 39, 'assistant', 'I\'d love to suggest an activity for you! Based on your state, you might enjoy playing **Calm Grid Sudoku** 🔢.

*A soothing number puzzle designed to cultivate focus and clarity*.

It\'s a wonderful, mindful way to take a break and ground yourself. I\'ve placed a quick link below to play it! 🌿', 0, '2026-06-18T15:54:11');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (69, 38, 'user', 'hii', 0, '2026-06-18T15:55:01');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (70, 38, 'assistant', 'Hello. This is a safe, non-judgmental space. What\'s going on for you today?', 0, '2026-06-18T15:55:01');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (71, 38, 'user', 'i feel sad', 0, '2026-06-18T15:55:08');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (72, 38, 'assistant', 'Feeling like you\'re just surviving, not living â€” that\'s a really important thing to name. You deserve more than just getting through. What did life feel like before this started?

🌴 *Tip: Sometimes a quiet distraction helps. Try escaping to the [Cozy Island Garden](/games/manorakshak_cozy_island_garden) activity.*', 0, '2026-06-18T15:55:08');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (73, 38, 'user', 'actually i have fight with all my friends', 0, '2026-06-18T15:55:30');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (74, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T15:55:30');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (75, 38, 'user', 'all friends are fighting', 0, '2026-06-18T15:55:41');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (76, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T15:55:41');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (77, 39, 'user', 'hello', 0, '2026-06-18T16:03:50');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (78, 39, 'assistant', 'Hi there! Welcome. This is a safe space for you. What\'s on your mind?', 0, '2026-06-18T16:03:50');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (79, 39, 'user', 'i am not anxious', 0, '2026-06-18T16:03:52');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (80, 39, 'assistant', 'Great to hear that! Even on good days, it can help to reflect a little. How has your day been overall?', 0, '2026-06-18T16:03:52');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (81, 39, 'user', 'what should i do when i fight with someone', 0, '2026-06-18T16:03:54');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (82, 39, 'assistant', 'Journalling can externalise overwhelming thoughts â€” getting them out of your head onto paper reduces their intensity. Try a brain dump: just write everything in your mind for 5 minutes, unedited.', 0, '2026-06-18T16:03:54');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (83, 39, 'user', 'suggest a game', 0, '2026-06-18T16:03:56');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (84, 39, 'assistant', 'I\'d love to suggest an activity for you! Based on your state, you might enjoy playing **Calm Grid Sudoku** 🔢.

*A soothing number puzzle designed to cultivate focus and clarity*.

It\'s a wonderful, mindful way to take a break and ground yourself. I\'ve placed a quick link below to play it! 🌿', 0, '2026-06-18T16:03:56');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (85, 39, 'user', 'actually i have fight with all my friends', 0, '2026-06-18T16:03:58');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (86, 39, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T16:03:58');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (87, 39, 'user', 'all friends are fighting', 0, '2026-06-18T16:04:00');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (88, 39, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T16:04:00');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (89, 39, 'user', 'hello', 0, '2026-06-18T16:05:02');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (90, 39, 'assistant', 'Hello! 🌸 I\'m really glad you\'re here. Whatever you\'re carrying right now, you don\'t have to carry it alone. How are you feeling today?', 0, '2026-06-18T16:05:02');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (91, 39, 'user', 'i am not anxious', 0, '2026-06-18T16:05:04');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (92, 39, 'assistant', 'Glad you\'re feeling okay! Sometimes even just checking in with yourself matters. Is there anything you\'d like to talk about?', 0, '2026-06-18T16:05:04');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (93, 39, 'user', 'what should i do when i fight with someone', 0, '2026-06-18T16:05:06');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (94, 39, 'assistant', 'For intrusive thoughts: don\'t try to force them away â€” that makes them louder. Try acknowledging them without engaging: \'I notice I\'m having the thought that...\' and let them pass like clouds.', 0, '2026-06-18T16:05:10');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (95, 39, 'user', 'suggest a game', 0, '2026-06-18T16:05:12');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (96, 39, 'assistant', 'I\'d love to suggest an activity for you! Based on your state, you might enjoy playing **Calm Grid Sudoku** 🔢.

*A soothing number puzzle designed to cultivate focus and clarity*.

It\'s a wonderful, mindful way to take a break and ground yourself. I\'ve placed a quick link below to play it! 🌿', 0, '2026-06-18T16:05:12');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (97, 39, 'user', 'actually i have fight with all my friends', 0, '2026-06-18T16:05:14');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (98, 39, 'assistant', 'Relationship pain can be some of the deepest pain there is. I\'m sorry you\'re going through this. Would you like to share more about what\'s happening?', 0, '2026-06-18T16:05:14');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (99, 39, 'user', 'all friends are fighting', 0, '2026-06-18T16:05:16');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (100, 39, 'assistant', 'Betrayal â€” especially infidelity â€” breaks something fundamental. It can make you question everything you knew. How are you processing what happened?', 0, '2026-06-18T16:05:16');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (101, 39, 'user', 'hello', 0, '2026-06-18T16:10:02');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (102, 39, 'assistant', 'Hey! I\'m here and listening. How has your day been?', 0, '2026-06-18T16:10:02');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (103, 39, 'user', 'i am not anxious', 0, '2026-06-18T16:10:04');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (104, 39, 'assistant', 'That\'s wonderful! 🌿 What\'s been going well for you lately, or is there something you\'d like to explore?', 0, '2026-06-18T16:10:04');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (105, 39, 'user', 'what should i do when i fight with someone', 0, '2026-06-18T16:10:06');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (106, 39, 'assistant', 'Journalling can externalise overwhelming thoughts â€” getting them out of your head onto paper reduces their intensity. Try a brain dump: just write everything in your mind for 5 minutes, unedited.', 0, '2026-06-18T16:10:06');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (107, 39, 'user', 'suggest a game', 0, '2026-06-18T16:10:08');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (108, 39, 'assistant', 'I\'d love to suggest an activity for you! Based on your state, you might enjoy playing **Calm Grid Sudoku** 🔢.

*A soothing number puzzle designed to cultivate focus and clarity*.

It\'s a wonderful, mindful way to take a break and ground yourself. I\'ve placed a quick link below to play it! 🌿', 0, '2026-06-18T16:10:08');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (109, 39, 'user', 'actually i have fight with all my friends', 0, '2026-06-18T16:10:10');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (110, 39, 'assistant', 'A relationship where your feelings are dismissed is slowly damaging. You deserve to be heard. Has this been the pattern throughout, or has something shifted?', 0, '2026-06-18T16:10:10');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (111, 39, 'user', 'all friends are fighting', 0, '2026-06-18T16:10:12');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (112, 39, 'assistant', 'Navigating relationships is hard, especially when trust has been broken. You deserve to feel safe and valued. What does the situation look like right now?', 0, '2026-06-18T16:10:12');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (113, 38, 'user', 'hi', 0, '2026-06-18T16:11:19');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (114, 38, 'assistant', 'Hello! 🌸 I\'m really glad you\'re here. Whatever you\'re carrying right now, you don\'t have to carry it alone. How are you feeling today?', 0, '2026-06-18T16:11:19');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (115, 38, 'user', 'actually i just fought with my friend today', 0, '2026-06-18T16:11:32');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (116, 38, 'assistant', 'Relationship pain can be some of the deepest pain there is. I\'m sorry you\'re going through this. Would you like to share more about what\'s happening?', 0, '2026-06-18T16:11:32');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (117, 38, 'user', 'yes she was wrong so  i just confronted her but it became worse', 0, '2026-06-18T16:11:49');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (118, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T16:11:49');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (119, 38, 'user', 'can you stop asking me just questions', 0, '2026-06-18T16:12:09');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (120, 38, 'assistant', 'I want to make sure I understand you properly. Could you share a little more about what you\'re feeling or going through? 🌿', 0, '2026-06-18T16:12:09');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (121, 39, 'user', 'hello', 0, '2026-06-18T16:59:01');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (122, 39, 'assistant', 'Hello! 🌸 I\'m really glad you\'re here. Whatever you\'re carrying right now, you don\'t have to carry it alone. How are you feeling today?', 0, '2026-06-18T16:59:01');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (123, 39, 'user', 'i am not anxious', 0, '2026-06-18T16:59:03');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (124, 39, 'assistant', 'Great to hear that! Even on good days, it can help to reflect a little. How has your day been overall?', 0, '2026-06-18T16:59:03');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (125, 39, 'user', 'what should i do when i fight with someone', 0, '2026-06-18T16:59:05');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (126, 39, 'assistant', 'Journalling can externalise overwhelming thoughts â€” getting them out of your head onto paper reduces their intensity. Try a brain dump: just write everything in your mind for 5 minutes, unedited.', 0, '2026-06-18T16:59:07');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (127, 39, 'user', 'suggest a game', 0, '2026-06-18T16:59:09');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (128, 39, 'assistant', 'I\'d love to suggest an activity for you! Based on your state, you might enjoy playing **Calm Grid Sudoku** 🔢.

*A soothing number puzzle designed to cultivate focus and clarity*.

It\'s a wonderful, mindful way to take a break and ground yourself. I\'ve placed a quick link below to play it! 🌿', 0, '2026-06-18T16:59:14');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (129, 39, 'user', 'actually i have fight with all my friends', 0, '2026-06-18T16:59:16');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (130, 39, 'assistant', 'Signs of emotional abuse â€” constant criticism, dismissiveness, control â€” can be subtle at first. Are you feeling safe in your relationship?', 0, '2026-06-18T16:59:16');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (131, 39, 'user', 'all friends are fighting', 0, '2026-06-18T16:59:18');
INSERT INTO `chat_messages` (`id`, `session_id`, `role`, `content`, `is_crisis`, `created_at`) VALUES (132, 39, 'assistant', 'When friends fight, it leaves you in a really difficult position, especially if you feel stuck in the middle or left out. Do you want to talk about what happened? ðŸŒ¿', 0, '2026-06-18T16:59:18');

-- ------------------------------------------------------
-- Table structure for table `chat_sessions`
-- ------------------------------------------------------
CREATE TABLE `chat_sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `session_id` varchar(36) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_session_id` (`session_id`),
  KEY `ix_chat_sessions_id` (`id`),
  KEY `ix_chat_session_id` (`session_id`),
  KEY `ix_chat_user` (`user_id`),
  CONSTRAINT `fk_chat_session_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=40 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `chat_sessions`
INSERT INTO `chat_sessions` (`id`, `user_id`, `session_id`, `title`, `created_at`, `updated_at`) VALUES (1, 2, 'default', NULL, '2026-05-14T20:44:43', '2026-05-14T20:44:43');
INSERT INTO `chat_sessions` (`id`, `user_id`, `session_id`, `title`, `created_at`, `updated_at`) VALUES (36, 13, 'test_session', NULL, '2026-06-18T13:38:54', '2026-06-18T13:39:23');
INSERT INTO `chat_sessions` (`id`, `user_id`, `session_id`, `title`, `created_at`, `updated_at`) VALUES (37, 13, 'test_session_proactive', NULL, '2026-06-18T13:39:43', '2026-06-18T15:08:20');
INSERT INTO `chat_sessions` (`id`, `user_id`, `session_id`, `title`, `created_at`, `updated_at`) VALUES (38, 3, 'local_web_session', NULL, '2026-06-18T13:42:16', '2026-06-18T16:12:09');
INSERT INTO `chat_sessions` (`id`, `user_id`, `session_id`, `title`, `created_at`, `updated_at`) VALUES (39, 13, 'test_session_validation', NULL, '2026-06-18T15:53:58', '2026-06-18T16:59:18');

-- ------------------------------------------------------
-- Table structure for table `diary_photos`
-- ------------------------------------------------------
CREATE TABLE `diary_photos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `entry_id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `url` varchar(500) NOT NULL,
  `uploaded_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ix_photo_entry` (`entry_id`),
  CONSTRAINT `fk_photo_entry` FOREIGN KEY (`entry_id`) REFERENCES `journal_entries` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `diary_photos`
INSERT INTO `diary_photos` (`id`, `entry_id`, `filename`, `url`, `uploaded_at`) VALUES (1, 6, 'a302a7065ec749f999db58ce7062af01.jpg', '/api/photos/a302a7065ec749f999db58ce7062af01.jpg', '2026-05-27T23:38:34');

-- ------------------------------------------------------
-- Table structure for table `diary_tags`
-- ------------------------------------------------------
CREATE TABLE `diary_tags` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `entry_id` int(11) NOT NULL,
  `tag` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_tag_entry` (`entry_id`),
  KEY `ix_tag_name` (`tag`),
  CONSTRAINT `fk_tag_entry` FOREIGN KEY (`entry_id`) REFERENCES `journal_entries` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `diary_tags`
INSERT INTO `diary_tags` (`id`, `entry_id`, `tag`) VALUES (4, 6, 'family');

-- ------------------------------------------------------
-- Table structure for table `game_progress`
-- ------------------------------------------------------
CREATE TABLE `game_progress` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `game_type` varchar(50) NOT NULL,
  `sessions` int(11) NOT NULL DEFAULT 0,
  `best_score` int(11) NOT NULL DEFAULT 0,
  `total_time` int(11) NOT NULL DEFAULT 0 COMMENT 'Total time in seconds',
  `last_played` datetime DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ix_game_progress_id` (`id`),
  KEY `ix_game_user` (`user_id`),
  KEY `ix_game_type` (`game_type`),
  CONSTRAINT `fk_game_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `game_progress`
-- No data to seed for `game_progress`

-- ------------------------------------------------------
-- Table structure for table `journal_entries`
-- ------------------------------------------------------
CREATE TABLE `journal_entries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `entry_date` date DEFAULT NULL,
  `title` varchar(300) DEFAULT NULL,
  `content` text NOT NULL,
  `mood_tag` varchar(50) DEFAULT NULL,
  `sentiment_score` float DEFAULT NULL,
  `stress_level` float DEFAULT NULL,
  `positivity_score` float DEFAULT NULL,
  `ai_insight` text DEFAULT NULL,
  `word_count` int(11) NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_date` (`user_id`,`entry_date`),
  KEY `ix_journal_entries_id` (`id`),
  KEY `ix_journal_user` (`user_id`),
  KEY `ix_journal_created` (`created_at`),
  CONSTRAINT `fk_journal_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `journal_entries`
INSERT INTO `journal_entries` (`id`, `user_id`, `entry_date`, `title`, `content`, `mood_tag`, `sentiment_score`, `stress_level`, `positivity_score`, `ai_insight`, `word_count`, `created_at`, `updated_at`) VALUES (1, 3, '2026-05-14', NULL, 'the day wasnt good', 'excited', NULL, NULL, NULL, NULL, 4, '2026-05-14T20:49:35', '2026-05-14T20:49:35');
INSERT INTO `journal_entries` (`id`, `user_id`, `entry_date`, `title`, `content`, `mood_tag`, `sentiment_score`, `stress_level`, `positivity_score`, `ai_insight`, `word_count`, `created_at`, `updated_at`) VALUES (2, 3, '2026-05-15', NULL, 'i feel lost today', 'happy', NULL, NULL, NULL, NULL, 4, '2026-05-15T14:26:03', '2026-05-15T14:26:03');
INSERT INTO `journal_entries` (`id`, `user_id`, `entry_date`, `title`, `content`, `mood_tag`, `sentiment_score`, `stress_level`, `positivity_score`, `ai_insight`, `word_count`, `created_at`, `updated_at`) VALUES (3, 3, '2026-05-23', NULL, '', 'calm', NULL, NULL, NULL, NULL, 0, '2026-05-24T00:55:11', '2026-05-24T00:55:12');
INSERT INTO `journal_entries` (`id`, `user_id`, `entry_date`, `title`, `content`, `mood_tag`, `sentiment_score`, `stress_level`, `positivity_score`, `ai_insight`, `word_count`, `created_at`, `updated_at`) VALUES (4, 3, '2026-05-24', NULL, '🎙️ Voice Journal:

hello hello', 'sad', NULL, NULL, NULL, NULL, 5, '2026-05-24T13:06:18', '2026-05-24T16:00:41');
INSERT INTO `journal_entries` (`id`, `user_id`, `entry_date`, `title`, `content`, `mood_tag`, `sentiment_score`, `stress_level`, `positivity_score`, `ai_insight`, `word_count`, `created_at`, `updated_at`) VALUES (5, 3, '2026-05-26', NULL, '', 'excited', NULL, NULL, NULL, NULL, 0, '2026-05-26T12:13:13', '2026-05-26T12:13:15');
INSERT INTO `journal_entries` (`id`, `user_id`, `entry_date`, `title`, `content`, `mood_tag`, `sentiment_score`, `stress_level`, `positivity_score`, `ai_insight`, `word_count`, `created_at`, `updated_at`) VALUES (6, 3, '2026-05-27', NULL, 'hii ', 'calm', NULL, NULL, NULL, NULL, 1, '2026-05-27T23:38:34', '2026-05-27T23:38:34');
INSERT INTO `journal_entries` (`id`, `user_id`, `entry_date`, `title`, `content`, `mood_tag`, `sentiment_score`, `stress_level`, `positivity_score`, `ai_insight`, `word_count`, `created_at`, `updated_at`) VALUES (7, 3, '2026-06-17', NULL, '', 'excited', NULL, NULL, NULL, NULL, 0, '2026-06-17T23:35:34', '2026-06-17T23:35:34');

-- ------------------------------------------------------
-- Table structure for table `mood_entries`
-- ------------------------------------------------------
CREATE TABLE `mood_entries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `mood_type` enum('happy','calm','sad','anxious','stressed','angry','lonely','tired','excited','grateful','neutral') NOT NULL,
  `intensity` int(11) NOT NULL DEFAULT 5,
  `note` text DEFAULT NULL,
  `sleep_hours` float DEFAULT NULL,
  `energy_level` int(11) NOT NULL DEFAULT 5,
  `logged_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ix_mood_entries_id` (`id`),
  KEY `ix_mood_user` (`user_id`),
  KEY `ix_mood_logged_at` (`logged_at`),
  CONSTRAINT `fk_mood_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `mood_entries`
-- No data to seed for `mood_entries`

-- ------------------------------------------------------
-- Table structure for table `therapists`
-- ------------------------------------------------------
CREATE TABLE `therapists` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `title` varchar(200) NOT NULL,
  `specialization` varchar(300) NOT NULL,
  `experience` int(11) NOT NULL,
  `rating` float NOT NULL,
  `fees` int(11) NOT NULL,
  `location` varchar(200) NOT NULL,
  `availability` varchar(200) NOT NULL,
  `contact_email` varchar(150) NOT NULL,
  `contact_phone` varchar(50) NOT NULL,
  `photo_url` varchar(300) NOT NULL,
  `bio` text NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_therapist_user` (`user_id`),
  CONSTRAINT `fk_therapist_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Dumping data for table `therapists`
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (1, 'Dr. Aarav Mehta', 'Consultant Psychiatrist', 'Depression, Bipolar Disorder, Mood Swings, Medication Management', 12, 4.8, 1500, 'Mumbai (Online / In-Person)', 'Mon-Wed, 10:00 AM - 4:00 PM', 'aarav.mehta@manorakshak.com', '+91 98765 43210', '/static/avatars/therapist_aarav.png', 'Dr. Aarav Mehta is a highly experienced psychiatrist specializing in mood disorders and medication-assisted therapy, focusing on a holistic recovery path.', '2026-06-17T01:00:23', NULL);
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (2, 'Ms. Ananya Sen', 'Clinical Psychologist & CBT Specialist', 'Anxiety, OCD, Stress Management, Cognitive Behavioral Therapy (CBT)', 8, 4.9, 1200, 'Delhi (Online)', 'Tue-Fri, 9:00 AM - 5:00 PM', 'ananya.sen@manorakshak.com', '+91 98765 43211', '/static/avatars/therapist_ananya.png', 'Ananya Sen specializes in CBT and mindfulness-based therapies to help clients navigate anxiety, panic attacks, and daily stress management.', '2026-06-17T01:00:23', NULL);
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (3, 'Dr. Rohan Deshmukh', 'Child & Adolescent Psychiatrist', 'ADHD, Teen Anxiety, Family Counseling, Behavioral Issues', 15, 4.7, 1800, 'Pune (Online / In-Person)', 'Mon-Thu, 2:00 PM - 7:00 PM', 'rohan.deshmukh@manorakshak.com', '+91 98765 43212', '/static/avatars/therapist_rohan.png', 'Dr. Rohan has extensive experience working with children, teenagers, and families to address developmental, behavioral, and academic challenges.', '2026-06-17T01:00:23', NULL);
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (4, 'Ms. Meera Nair', 'Trauma-Informed Counseling Psychologist', 'Trauma Recovery, Grief Counseling, Self-Esteem, Relationship Advice', 6, 4.9, 1000, 'Bengaluru (Online)', 'Wed-Sat, 11:00 AM - 6:00 PM', 'meera.nair@manorakshak.com', '+91 98765 43213', '/static/avatars/therapist_meera.png', 'Meera Nair is dedicated to providing a safe, non-judgmental space for clients recovering from trauma, grief, or navigating difficult relationship transitions.', '2026-06-17T01:00:23', NULL);
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (5, 'Dr. Shalini Kapoor', 'Neuropsychiatrist', 'Sleep Disorders, ADHD, Chronic Stress, Cognitive Rehabilitation', 10, 4.8, 1600, 'Hyderabad (Online / In-Person)', 'Mon-Fri, 10:00 AM - 1:00 PM', 'shalini.kapoor@manorakshak.com', '+91 98765 43214', '/static/avatars/therapist_shalini.png', 'Dr. Shalini Kapoor focuses on the intersection of neurological health and psychiatric well-being, helping clients with sleep, attention, and chronic stress issues.', '2026-06-17T01:00:23', NULL);
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (6, 'Anxiety, CBT, Depression', 'Licensed Psychiatrist', 'Anxiety, CBT, Depression', 10, 5.0, 1200, 'Mumbai Wellness Center', 'Mon-Fri: 10 AM - 6 PM', 'aarav.mehta@therapist.com', '+91 99887 76655', '/static/avatars/therapist_default.png', 'Helping you find balance and peace.', '2026-06-17T01:28:31', 7);
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (7, 'Jyoti Borse', 'MD', 'Anxiety,  Depression', 9, 5.0, 2000, 'Dhule', 'Mon: Fri: 10:00am to 6:00 pm', 'jyotiborse124@gmail.com', '9561361587', '/static/avatars/therapist_default.png', 'experienced therapist', '2026-06-17T01:39:54', 9);
INSERT INTO `therapists` (`id`, `name`, `title`, `specialization`, `experience`, `rating`, `fees`, `location`, `availability`, `contact_email`, `contact_phone`, `photo_url`, `bio`, `created_at`, `user_id`) VALUES (8, 'Dr. Integration Tester', 'MD, Psychiatrist', 'CBT, Depression, Anxiety', 15, 5.0, 2000, 'Integration Clinic', 'Mon-Fri: 10 AM - 4 PM', 'integration_therapist@example.com', '+91 99999 88888', '/static/avatars/therapist_default.png', 'Expert in integration testing and clinical therapy.', '2026-06-17T22:58:25', 10);

-- ------------------------------------------------------
-- Table structure for table `users`
-- ------------------------------------------------------
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `username` varchar(100) NOT NULL,
  `full_name` varchar(200) DEFAULT NULL,
  `hashed_password` varchar(255) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `dark_mode` tinyint(1) NOT NULL DEFAULT 0,
  `wellness_streak` int(11) NOT NULL DEFAULT 0,
  `last_active_date` datetime DEFAULT NULL,
  `avatar_emoji` varchar(10) DEFAULT '?',
  `bio` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `game_progress_json` longtext DEFAULT NULL,
  `role` varchar(50) DEFAULT 'user',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_email` (`email`),
  UNIQUE KEY `uq_users_username` (`username`),
  KEY `ix_users_id` (`id`),
  KEY `ix_users_email` (`email`),
  KEY `ix_users_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `users`
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (1, 'test@mindcare.com', 'testuser', 'Test User', 'scrypt:32768:8:1$jF6CAfTHCvlVxeZM$5fbcaa5d5830eba0430b2453d72bc765cfa047d4ccc8f66d577d841c0c8c31e22a3ea1ff9b8fdd3782210cb973dc1f2dbe3eaf49312fea97bb1e64bdd7934c9c', 1, 0, 0, NULL, '🌿', NULL, '2026-05-14T20:39:02', '2026-05-14T20:39:02', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (2, 'demo@mindcare.com', 'demo', 'Demo', 'scrypt:32768:8:1$7SeH8UgBOCC0L0Es$a4f440ad09695b5c594fa8da06b2f2150ff035d6990526a8fd91be25514eb2779c73fae9a4bb297178cf79f3925d949c8e3f71e1a0405c636936b0b0ea8454b3', 1, 0, 0, NULL, '🌿', NULL, '2026-05-14T20:41:44', '2026-05-14T20:41:44', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (3, 'kartikaborse87@gmail.com', 'kartikaborse87', 'Kartika Borse', 'scrypt:32768:8:1$ci3wxib9ixxq6TSQ$568785c780ed9e51035fdd3a498cc374e8e9e811a2f3abaf61d8a616ddbe7cfea8fd92ab1bb5ad58f16145436396e580f310b0095f071fbf72f5aa16d3e89850', 1, 0, 0, '2026-06-17T19:14:37', '🌿', NULL, '2026-05-14T20:47:57', '2026-06-17T19:14:37', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (4, 'test2@test.com', 'test2', 'Test User', 'scrypt:32768:8:1$lYmTgebzA4nanDbu$0cab2177ffdda80bd6ff541ca0eae222eba5803a481749c22b88302e66a2e81c14f15c6eddb81171e6c6dbb37841d4d7b8b14608953da945274357d8d3933786', 1, 0, 0, '2026-05-24T00:10:07', '🌿', NULL, '2026-05-23T23:32:40', '2026-05-24T00:10:07', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (6, 'user1234@mindcare.com', 'user1234', 'Test User', 'scrypt:32768:8:1$NsbpCDUeG8cx0eQY$2d054bf14a6aa7213f156023af1f30f1450d740e568f7702c323901a721493a703fa978adfbe40eddc51d706be1e64c3fe4f094b1146caedbff2dd0fb496e34f', 1, 0, 0, NULL, '🌿', NULL, '2026-05-24T12:21:24', '2026-05-24T12:21:24', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (7, 'aarav.mehta@therapist.com', '10', 'Anxiety, CBT, Depression', 'scrypt:32768:8:1$MGNTOr4ONx1Gr0ED$415c01aabd5a8dd138b26f1acb2bc53cbe3defee815c7adef04df754edcccf14fe53b3ba68f0089d1d77a34c7d26bd819bb7cb06ee16553f80fce79395856f2c', 1, 0, 0, '2026-06-17T02:01:25', '🌸', NULL, '2026-06-17T01:18:52', '2026-06-17T02:01:25', NULL, 'therapist');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (8, 'jane.doe@gmail.com', 'jane.doe', 'Jane Doe', 'scrypt:32768:8:1$PbqVNnleBAEvBM8H$47a45a3c84ed9a0f8867bbc30c1305edce00c274ac8e2277443352c38d7a26d0d60e3cb079e82664091d68f21e751669e485f97b257016d14d34055571f520c6', 1, 0, 0, '2026-06-17T02:04:28', '?', NULL, '2026-06-17T01:32:47', '2026-06-17T02:04:28', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (9, 'jyotiborse124@gmail.com', 'jyotiborse124', 'Jyoti Borse', 'scrypt:32768:8:1$NzYButXswyu92Na2$707ef8d510223d9a34724b7da20739f9df35df1099840bd21bced3cd66f8a732483fc31af284e71d1c9220230853a72b97b719c8d638dd195656e5f3fc71ea3b', 1, 0, 0, '2026-06-17T22:57:31', '🧘', NULL, '2026-06-17T01:38:11', '2026-06-17T22:57:31', NULL, 'therapist');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (10, 'integration_therapist@example.com', 'integ_therapist', 'Dr. Integration Tester', 'scrypt:32768:8:1$8S19CyCzCkEOARE1$0b1b868faf7c84d17518a00015325df7306e69dfee7d905a30edaa41063457df00d38c94779e36108d172e3f0914928d8d7b9e4272e85c71744a21a21733029f', 1, 0, 0, '2026-06-17T23:00:15', '🧘', NULL, '2026-06-17T22:58:17', '2026-06-17T23:00:15', NULL, 'therapist');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (11, 'integration_patient@example.com', 'integ_patient', 'Alice Patient', 'scrypt:32768:8:1$425IYQCEsy5KKzvA$57f688f49241f60d0be646bd1fe21500f0d28e0eca89b5ae70ade345d8c17ca00263c9ec024c4f07d14b36f593d502c79ac9cdbda3861648212dd3ebecf7a142', 1, 0, 0, '2026-06-17T23:00:29', '?', NULL, '2026-06-17T22:58:30', '2026-06-17T23:00:29', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (12, 'clinical_therapist@example.com', 'clinical_t', 'Dr. Clinical Reviewer', 'scrypt:32768:8:1$UenLQaSrw9lNXNz8$ce99855317d6ba4d4d8d7a92201c8585cbae01342a1432e381a38167cfaa67cf64d712e7ec9c2a7841186a4c52f0844a778bde67fe8143ed7b0880355fa52b70', 1, 0, 0, NULL, '?', NULL, '2026-06-17T23:18:13', '2026-06-17T23:18:13', NULL, 'therapist');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (13, 'clinical_patient@example.com', 'clinical_p', 'Bob Patient', 'scrypt:32768:8:1$0wikHTY8TxdmQytV$fe12a552b925f965e79487cbaec3d1e14b9e03049482f94dab9565a3692630cc1a847e6be2693cef29c8b66755879ceb9758359c3d7d142319fae6b41f65f2af', 1, 0, 0, '2026-06-18T16:58:58', '?', NULL, '2026-06-17T23:18:15', '2026-06-18T16:58:58', NULL, 'user');
INSERT INTO `users` (`id`, `email`, `username`, `full_name`, `hashed_password`, `is_active`, `dark_mode`, `wellness_streak`, `last_active_date`, `avatar_emoji`, `bio`, `created_at`, `updated_at`, `game_progress_json`, `role`) VALUES (16, 'clinical_patient2@example.com', 'clinical_p2', 'Bob Patient Two', 'scrypt:32768:8:1$urbBTP5tDJJpqiYc$ba4b4394daa8df06e2fce5b42ec043a65dfa0a300eddc350e1a3c7dcf51e1ac2178812135cda614aea4bbf1d3962a63bae921f0cb6b4cba0f68dfdaf653c2fad', 1, 0, 0, NULL, '?', NULL, '2026-06-18T13:38:49', '2026-06-18T13:38:49', NULL, 'user');

-- ------------------------------------------------------
-- Table structure for table `wellness_scores`
-- ------------------------------------------------------
CREATE TABLE `wellness_scores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `score` float NOT NULL DEFAULT 0,
  `mood_score` float NOT NULL DEFAULT 0,
  `journal_score` float NOT NULL DEFAULT 0,
  `sentiment_score` float NOT NULL DEFAULT 0,
  `streak_score` float NOT NULL DEFAULT 0,
  `calculated_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ix_wellness_scores_id` (`id`),
  KEY `ix_wellness_user` (`user_id`),
  CONSTRAINT `fk_wellness_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `victim_profiles`
-- ------------------------------------------------------
CREATE TABLE IF NOT EXISTS `victim_profiles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL UNIQUE,
  `case_number` varchar(100) NOT NULL UNIQUE,
  `category` varchar(150) NOT NULL,
  `judicial_stage` varchar(100) DEFAULT 'Investigation',
  `counselor_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`counselor_id`) REFERENCES `therapists` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ------------------------------------------------------
-- Table structure for table `victim_distress_scores`
-- ------------------------------------------------------
CREATE TABLE IF NOT EXISTS `victim_distress_scores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `score` float NOT NULL,
  `sentiment_score` float DEFAULT NULL,
  `vocal_stress` float DEFAULT NULL,
  `assessment_score` int(11) DEFAULT NULL,
  `details_json` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ------------------------------------------------------
-- Table structure for table `victim_alerts`
-- ------------------------------------------------------
CREATE TABLE IF NOT EXISTS `victim_alerts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `score` float NOT NULL,
  `reason` text NOT NULL,
  `status` varchar(50) DEFAULT 'Active',
  `resolution_notes` text DEFAULT NULL,
  `resolved_by` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `resolved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ------------------------------------------------------
-- Table structure for table `victim_vault_incidents`
-- ------------------------------------------------------
CREATE TABLE IF NOT EXISTS `victim_vault_incidents` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `incident_type` varchar(100) NOT NULL,
  `description` text NOT NULL,
  `evidence_file_path` varchar(255) DEFAULT NULL,
  `threat_severity` varchar(20) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ------------------------------------------------------
-- Table structure for table `victim_sos_alerts`
-- ------------------------------------------------------
CREATE TABLE IF NOT EXISTS `victim_sos_alerts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `latitude` varchar(50) NOT NULL,
  `longitude` varchar(50) NOT NULL,
  `status` varchar(50) DEFAULT 'Active',
  `dispatched_officer` varchar(150) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ------------------------------------------------------
-- Table structure for table `victim_compensation_claims`
-- ------------------------------------------------------
CREATE TABLE IF NOT EXISTS `victim_compensation_claims` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `case_number` varchar(100) NOT NULL,
  `amount_entitled` float NOT NULL,
  `stage` varchar(100) NOT NULL,
  `status` varchar(50) DEFAULT 'Pending Officer Review',
  `petition_text` text NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS = 1;
