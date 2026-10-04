-- Email a notification on each new submission: pg_net posts the row to the
-- contact-notify Edge Function, which sends via Brevo. Async and non-blocking —
-- a failed notification never blocks or rolls back the insert itself.
--
-- Apply this AFTER deploying the Edge Function (it references the function URL).
-- Replace <REF> with the Supabase project ref.

create extension if not exists pg_net with schema extensions;

create or replace function public.notify_contact_submission()
returns trigger
language plpgsql
security definer
set search_path = public, extensions
as $$
begin
  perform net.http_post(
    url := 'https://<REF>.supabase.co/functions/v1/contact-notify',
    headers := jsonb_build_object('Content-Type', 'application/json'),
    body := jsonb_build_object('record', to_jsonb(new))
  );
  return new;
end;
$$;

drop trigger if exists contact_submission_notify on public.contact_submissions;
create trigger contact_submission_notify
  after insert on public.contact_submissions
  for each row execute function public.notify_contact_submission();
