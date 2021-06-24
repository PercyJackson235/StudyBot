# StudyBot
StudyBot is a Discord Bot written in Python 3 using discord.py.
Originally developed for use in the [Python Practice Discord](htps://discord.gg/UBUx88xVZh), 
StudyBot if Free and Open-Source. 

StudyBot has a few basic features:
- Users can add time to the study time counter with !add-time
- Users can check their personal study time counter, or the global study time counter with !get-time and !all-time
- Users can invite themselves to a linked GitHub organization with !github-join

## Usage
- Clone this repository to your local environment.
- Install the project requirements in `requirements.txt`
- Create a `.env` file with the following key-value pairs in the root directory:
    - DISCORD_TOKEN
    - ADMIN_ROLE_ID
    - CHANNEL_ID
    - GITHUB_ORG_NAME
    - GITHUB_API_KEY
- Run `studybot.py`