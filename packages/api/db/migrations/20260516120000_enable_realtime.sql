-- Enable Supabase Realtime for demo dashboard (TASK-012)
ALTER PUBLICATION supabase_realtime ADD TABLE audit_log;
ALTER PUBLICATION supabase_realtime ADD TABLE queries;
