CREATE TABLE `event_submissions` (
	`id` text PRIMARY KEY NOT NULL,
	`url` text NOT NULL,
	`proposal` text NOT NULL,
	`created_at` text NOT NULL,
	`daily_client` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `event_submissions_url_unique` ON `event_submissions` (`url`);--> statement-breakpoint
CREATE INDEX `submissions_created` ON `event_submissions` (`created_at`);--> statement-breakpoint
CREATE INDEX `submissions_client` ON `event_submissions` (`daily_client`);