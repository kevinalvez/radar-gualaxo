"""
config/schedule.py

Orchestration (background-run) configuration: how often the monitor
should run unattended, at what time (time, "HH:MM"), which search period
each run should use ("period" - same options as the Busca tab: "24h",
"7_days", "30_days", "custom" with explicit start_date/end_date -
"DD/MM/YYYY" strings, chosen independently of how often it runs), and
which keywords/sources that unattended run should use - a selection kept
independent from whatever's checked in the Busca tab for a one-off run.

Note on "custom" + a recurring schedule: a fixed start_date/end_date
applies to *every* future automatic run, not a rolling window - if the
periodicity is "every 2 days" but the period is a fixed custom range,
every run searches that same historical range again. That's what was
asked for; it's just worth knowing going in, since it doesn't behave
like "24h"/"7_days"/"30_days" do (those already always mean "relative to
whenever this particular run happens").

Two mutually exclusive periodicity modes (picked via "mode"):
    "interval" - every interval_days days
    "weekdays" - on specific days of the week (weekdays), every week

weekdays uses APScheduler's own day_of_week codes directly
("mon".."sun") so config/schedule.py -> CronTrigger needs no translation
step - see interface_web/app.py's _reschedule_orchestration().

Centered on one JSON file (config/data/schedule.json), same as
sources.json/keywords.json, specifically so this can be the single
source of truth if orchestration settings ever get edited from more than
one machine.

This module only persists the setting - interface_web/app.py's
APScheduler is what actually reads it and fires runs.
"""

from config.json_storage import load_json, save_json


FILE = "schedule.json"

DEFAULT = {
    "mode": "interval",
    "interval_days": None,
    "weekdays": [],
    "time": None,
    "period": "7_days",
    "start_date": None,
    "end_date": None,
    "keywords": [],
    "sources": [],
}


def load_schedule():

    data = load_json(FILE)

    if not isinstance(data, dict):
        return dict(DEFAULT)

    return {**DEFAULT, **data}


def save_schedule(schedule: dict):

    save_json(FILE, schedule)
