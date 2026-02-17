import os
import requests
import re
from datetime import datetime
print(f"DEBUG: Script started. Token length: {len(os.getenv('GITHUB_TOKEN', ''))}")

USERNAME = "ProGamingZ"
TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def run_query(query):
    request = requests.post(
        "https://api.github.com/graphql",
        json={"query": query},
        headers=HEADERS
    )
    
    # Check for HTTP errors (like 401 or 404)
    if request.status_code != 200:
        print(f"HTTP Error {request.status_code}: {request.text}")
        raise Exception(f"GitHub API returned status code {request.status_code}")

    result = request.json()

    # Check for GraphQL-specific errors
    if "errors" in result:
        print("GraphQL Errors found:")
        for error in result["errors"]:
            print(f"-- {error.get('message')}")
        raise Exception("GraphQL query failed.")
    
    if "data" not in result or not result["data"]:
         print(f"Unexpected response body: {result}")
         raise KeyError("The 'data' field is missing from the response.")
         
    return result


def calculate_streaks(days):
    """Calculate current and longest streak from contribution days."""
    
    # Remove today if zero contributions
    today_str = datetime.now().strftime('%Y-%m-%d')
    if days and days[-1]['date'] == today_str and days[-1]['contributionCount'] == 0:
        days = days[:-1]

    # Current streak
    current_streak = 0
    current_start = None
    current_end = None

    for day in reversed(days):
        if day['contributionCount'] > 0:
            current_streak += 1
            current_start = day['date']
            if current_end is None:
                current_end = day['date']
        else:
            break

    # Longest streak
    longest_streak = 0
    longest_start = None
    longest_end = None

    temp_streak = 0
    temp_start = None

    for day in days:
        if day['contributionCount'] > 0:
            temp_streak += 1
            if temp_start is None:
                temp_start = day['date']
        else:
            if temp_streak > longest_streak:
                longest_streak = temp_streak
                longest_start = temp_start
                longest_end = prev_day
            temp_streak = 0
            temp_start = None
        prev_day = day['date']

    # Check last streak in case it ends on last day
    if temp_streak > longest_streak:
        longest_streak = temp_streak
        longest_start = temp_start
        longest_end = days[-1]['date']

    def fmt_date(d_str):
        if not d_str:
            return ""
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        return dt.strftime("%-m/%-d/%y")

    current_dates = (
        f"({fmt_date(current_start)} - {fmt_date(current_end)})"
        if current_streak > 0 else ""
    )

    longest_dates = (
        f"({fmt_date(longest_start)} - {fmt_date(longest_end)})"
        if longest_streak > 0 else ""
    )

    return current_streak, current_dates, longest_streak, longest_dates


def get_stats():
    print("Hello World - Fetching GitHub Stats...")
    query = f"""
    {{
      user(login: "{USERNAME}") {{
        contributionsCollection {{
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                contributionCount
                date
              }}
            }}
          }}
        }}
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {{
          nodes {{
            stargazerCount
            languages(first: 5) {{
              edges {{
                size
                node {{
                  name
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """

    result = run_query(query)
    data = result["data"]["user"]

    contrib_data = data["contributionsCollection"]
    total_commits = contrib_data["totalCommitContributions"]
    total_prs = contrib_data["totalPullRequestContributions"]
    total_issues = contrib_data["totalIssueContributions"]
    total_contributions = contrib_data["contributionCalendar"]["totalContributions"]

    # Stars and languages
    total_stars = 0
    lang_stats = {}

    for repo in data["repositories"]["nodes"]:
        total_stars += repo["stargazerCount"]
        for lang in repo["languages"]["edges"]:
            name = lang["node"]["name"]
            size = lang["size"]
            lang_stats[name] = lang_stats.get(name, 0) + size

    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)
    top_langs = [l[0] for l in sorted_langs[:8]]

    # Flatten days
    calendar_weeks = contrib_data["contributionCalendar"]["weeks"]
    days = [d for w in calendar_weeks for d in w["contributionDays"]]

    current_streak, current_dates, longest_streak, longest_dates = calculate_streaks(days)

    return {
        "contribs": total_contributions,
        "commits": total_commits,
        "prs": total_prs,
        "issues": total_issues,
        "stars": total_stars,
        "streak_curr": current_streak,
        "streak_curr_dates": current_dates,
        "streak_long": longest_streak,
        "streak_long_dates": longest_dates,
        "langs": ", ".join(top_langs)
    }

def update_readme(stats):
    print("Hello World - Attempting to update README...")   
    html_content = f"""
<table>
  <thead>
    <tr>
      <th colspan="2" align="center"> GitHub Activity</th>
      <th colspan="2" align="center"> Streaks & Languages</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Total Contributions</strong></td>
      <td>{stats['contribs']}</td>
      <td><strong>Current Streak</strong></td>
      <td>{stats['streak_curr']} <span>{stats['streak_curr_dates']}</span></td>
    </tr>
    <tr>
      <td><strong>Total Commits</strong></td>
      <td>{stats['commits']}</td>
      <td><strong>Longest Streak</strong></td>
      <td>{stats['streak_long']} <span>{stats['streak_long_dates']}</span></td>
    </tr>
    <tr>
      <td><strong>Total Pull Requests</strong></td>
      <td>{stats['prs']}</td>
      <td><strong>Spoken Languages</strong></td>
      <td>English, Filipino</td>
    </tr>
    <tr>
      <td><strong>Total Issues</strong></td>
      <td>{stats['issues']}</td>
      <td rowspan="2" valign="top"><strong>Programming Languages</strong></td>
      <td rowspan="2" valign="top">{stats['langs']}</td>
    </tr>
    <tr>
      <td><strong>Total Stars</strong></td>
      <td>{stats['stars']}</td>
    </tr>
  </tbody>
</table>
"""


    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    pattern = r"(<!-- STATS:START -->)([\s\S]*?)(<!-- STATS:END -->)"
    replacement = r"\1\n" + html_content + r"\n\3"

    new_readme = re.sub(pattern, replacement, readme)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)
    print("HELLO WORLD")

if __name__ == "__main__":
    print("Hello World - Script Started!")
    try:
        stats = get_stats()
        update_readme(stats)
        print("README updated successfully!")
    except Exception as e:
        print(f"Error: {e}")
