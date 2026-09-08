import {sqliteTable, text, index} from 'drizzle-orm/sqlite-core';
export const submissions = sqliteTable('event_submissions', {
  id: text('id').primaryKey(),
  url: text('url').notNull().unique(),
  proposal: text('proposal').notNull(),
  createdAt: text('created_at').notNull(),
  dailyClient: text('daily_client').notNull(),
}, table => [index('submissions_created').on(table.createdAt), index('submissions_client').on(table.dailyClient)]);
