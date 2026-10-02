# Backups

Your memories and original files are personal data. They are **not**
in Git, so they need their own backups.

## Back up

    ./scripts/backup.sh

Creates `backups/<timestamp>/` with the database, every original file,
and fingerprints. Then **download that folder to your own computer** —
a backup that only exists on the Codespace disappears with it.

## Prove a backup works

    ./scripts/verify_backup.sh backups/<timestamp>

Restores into a throwaway database, counts what came back, deletes the
throwaway. Your real data is never touched.

## Restore

    ./scripts/restore.sh backups/<timestamp>

Asks you to type `RESTORE`, and backs up the current state first.

## How often

At the end of any session where you recorded something you'd hate to lose.