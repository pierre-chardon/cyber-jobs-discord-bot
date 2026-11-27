# Cyber Jobs Discord Bot

*[Version française plus bas](#version-française)*

A small Discord bot that posts **new cybersecurity and networking job offers in France and Switzerland** to Discord, each country in its own channel. It was built for a private Discord server that brings together a cohort of cybersecurity students (Jedha, Fullstack Cyber), to help them find internships and jobs after their training.

## What it does

Every 30 minutes, a GitHub Actions workflow runs `bot_offres.py`, which:

1. collects job offers from several public sources (see below);
2. keeps only cybersecurity and networking roles (SOC, pentest, GRC, CTI, security engineer, network engineer or architect…), in French, English or German, and sorts them by country;
3. removes duplicates, including the same offer seen on two different sites;
4. posts each new offer to Discord through a webhook, as a card showing the title, company, location, contract type and a link to the original offer.

On its first run, the bot only records the offers already online and posts a short confirmation message, so the channel is not flooded.

## Sources

| Source | How it is used | Required secrets |
| --- | --- | --- |
| Company career pages (Lever, Greenhouse) | Public job board APIs of the companies listed in `entreprises.json` | none |
| [Jooble](https://jooble.org/api/about) | Job aggregator API, 3 searches per hour and per country (free tier: 100 per day per key) | `JOOBLE_KEY` (France), `JOOBLE_KEY_CH` (Switzerland) |
| [Adzuna](https://developer.adzuna.com) | Job aggregator API (paid), disabled unless keys are set | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` |
| [France Travail](https://francetravail.io) | Official API "Offres d'emploi v2", disabled unless keys are set | `FT_CLIENT_ID`, `FT_CLIENT_SECRET` |

Each source is optional: if its keys are missing, the bot simply skips it.

## Setup

1. **Discord**: in the target channel, go to *Settings › Integrations › Webhooks*, create a webhook and copy its URL.
2. **GitHub**: fork or copy this repository, then add the webhook URLs and any API keys under *Settings › Secrets and variables › Actions*. A country is only processed if its webhook is set: `DISCORD_WEBHOOK` (France), `DISCORD_WEBHOOK_CH` (Switzerland).
3. **Run**: open the *Actions* tab, select *Offres cyber* and click *Run workflow* to test. The schedule then runs automatically every 30 minutes.

## Configuration

- **Companies**: add or remove companies in `entreprises.json`. The identifier is the word after `jobs.lever.co/` or `job-boards.greenhouse.io/` in the company's job page URL.
- **Area**: set `ZONE` in `.github/workflows/offres.yml` to `France` (default) or `Ile-de-France`, and `ZONE_CH` for Switzerland.
- **Countries**: the `PAYS` settings at the top of `bot_offres.py` (keywords, cities, memory file) make it easy to add another country.
- **Keywords and filters**: `RECHERCHES_JOOBLE`, `RECHERCHES_ADZUNA` and `FILTRE_INTITULE` at the top of `bot_offres.py`.
- **Test without posting**: run locally with `DRY_RUN=1 python bot_offres.py`.

## Data and privacy

- **No personal data is collected.** The bot only reads public job offers; it does not read Discord messages or any information about server members.
- **Minimal storage.** The only stored data is `deja_publiees.json` (and `deja_publiees_ch.json` for Switzerland): the identifiers of offers already posted, kept for 60 days at most, only to avoid duplicates. Offer descriptions are never stored.
- **Limited display.** Only the title, company, location, contract type and date are shown, always with a link to the original offer and its source. Full descriptions are not copied.
- **No AI.** No data is used to train or feed an artificial intelligence model.
- **Non-commercial.** The project is free, has no ads, and no data is sold or shared.
- **Secrets** (webhook URL, API keys) are stored as encrypted GitHub Actions secrets and never appear in the code.

## Contact

Pierre Chardon · [LinkedIn](https://www.linkedin.com/in/pierre-chardon-cyb/)

---

## Version française

Un petit bot Discord qui publie les **nouvelles offres d'emploi en cybersécurité et en réseau en France et en Suisse**, chaque pays dans son propre salon. Il a été créé pour un serveur Discord privé qui réunit une promotion d'étudiants en cybersécurité (Jedha, parcours Fullstack Cyber), afin de les aider à trouver un stage ou un emploi après la formation.

### Fonctionnement

Toutes les 30 minutes, un workflow GitHub Actions lance `bot_offres.py`, qui :

1. récupère les offres de plusieurs sources publiques (voir le tableau ci-dessus) ;
2. ne garde que les postes cyber et réseau (SOC, pentest, GRC, CTI, ingénieur sécurité, ingénieur ou architecte réseau…), en français, anglais ou allemand, et les trie par pays ;
3. supprime les doublons, y compris une même offre vue sur deux sites ;
4. publie chaque nouvelle offre sur Discord via un webhook, sous forme de carte : intitulé, entreprise, lieu, type de contrat et lien vers l'offre d'origine.

Au premier lancement, le bot mémorise les offres déjà en ligne sans les publier, et poste simplement un message de confirmation.

### Données et confidentialité

- **Aucune donnée personnelle n'est collectée.** Le bot lit uniquement des offres d'emploi publiques ; il ne lit ni les messages Discord ni aucune information sur les membres du serveur.
- **Conservation minimale.** Seuls les fichiers `deja_publiees.json` et `deja_publiees_ch.json` sont conservés : les identifiants des offres déjà publiées, pendant 60 jours au maximum, uniquement pour éviter les doublons. Les descriptions des offres ne sont jamais stockées.
- **Affichage limité.** Seuls l'intitulé, l'entreprise, le lieu, le type de contrat et la date sont affichés, toujours avec un lien vers l'offre d'origine et sa source. Les descriptions complètes ne sont pas reprises.
- **Pas d'IA.** Aucune donnée n'est utilisée pour entraîner ou alimenter un modèle d'intelligence artificielle.
- **Usage non commercial.** Le projet est gratuit, sans publicité, et aucune donnée n'est revendue ni partagée.
- **Secrets** (adresse du webhook, clés d'API) : stockés dans les secrets chiffrés de GitHub Actions, ils n'apparaissent jamais dans le code.

### Contact

Pierre Chardon · [LinkedIn](https://www.linkedin.com/in/pierre-chardon-cyb/)
