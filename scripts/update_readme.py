import os
import requests
import re
from datetime import datetime

USERNAME = "ProGamingZ"
TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"bearer {TOKEN}"}

def run_query(query):
    request = requests.post('https://api.github.com/graphql', json={'query': query}, headers=HEADERS)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(f"Query failed: {request.status_code}")

def get_stats():
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
            stargazersCount
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
    data = result['data']['user']
    
    total_commits = data['contributionsCollection']['totalCommitContributions']
    total_prs = data['contributionsCollection']['totalPullRequestContributions']
    total_issues = data['contributionsCollection']['totalIssueContributions']
    total_contributions = data['contributionsCollection']['contributionCalendar']['totalContributions']
    
    total_stars = 0
    lang_stats = {}
    
    for repo in data['repositories']['nodes']:
        total_stars += repo['stargazersCount']
        for lang in repo['languages']['edges']:
            name = lang['node']['name']
            size = lang['size']
            lang_stats[name] = lang_stats.get(name, 0) + size
            
    sorted_langs = sorted(lang_stats.items(), key=lambda item: item[1], reverse=True)
    top_langs = [l[0] for l in sorted_langs[:8]]
    
    calendar_weeks = data['contributionsCollection']['contributionCalendar']['weeks']
    days = []
    for week in calendar_weeks:
        for day in week['contributionDays']:
            days.append(day) 
            
    today_str = datetime.now().strftime('%Y-%m-%d')
    idx = len(days) - 1
    if days[idx]['date'] == today_str and days[idx]['contributionCount'] == 0:
        idx -= 1 

    current_streak = 0
    current_start = None
    current_end = days[idx]['date']
    
    while idx >= 0:
        if days[idx]['contributionCount'] > 0:
            current_streak += 1
            current_start = days[idx]['date']
        else:
            break 
        idx -= 1
        
    def fmt_date(d_str):
        if not d_str: return ""
        dt = datetime.strptime(d_str, '%Y-%m-%d')
        return dt.strftime('%-m/%-d/%y')

    curr_dates = f"({fmt_date(current_start)} - {fmt_date(current_end)})" if current_streak > 0 else ""
    longest_streak = current_streak 
    long_dates = curr_dates

    return {
        "contribs": total_contributions,
        "commits": total_commits,
        "prs": total_prs,
        "issues": total_issues,
        "stars": total_stars,
        "streak_curr": current_streak,
        "streak_curr_dates": curr_dates,
        "streak_long": longest_streak, 
        "streak_long_dates": long_dates,
        "langs": ", ".join(top_langs)
    }

def update_readme(stats):
    html_content = f"""
<table>
  <tr>
    <td valign="top" width="50%">
      <b>My Github Statistics</b><br><br>
      Total Contributions &nbsp; {stats['contribs']}<br>
      Total Commits &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {stats['commits']}<br>
      Total Pull Requests &nbsp; {stats['prs']}<br>
      Total Issues &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {stats['issues']}<br>
      Total Stars &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {stats['stars']}<br>
      Current Streak &nbsp; &nbsp; &nbsp; &nbsp; {stats['streak_curr']} &nbsp; <span style="color:gray; font-size:12px">{stats['streak_curr_dates']}</span><br>
      Longest Streak &nbsp; &nbsp; &nbsp; &nbsp; {stats['streak_long']} &nbsp; <span style="color:gray; font-size:12px">{stats['streak_long_dates']}</span>
    </td>
    <td valign="top" width="50%">
      <b>Programming Languages Used:</b><br><br>
      {stats['langs']}
    </td>
  </tr>
</table>
"""
    
    with open("README.md", "r", encoding="utf-8") as file:
        readme = file.read()

   # THE PATTERN: Encasing the symbols with your tags
    pattern = r"[\s\S]*?"
    
    # THE REPLACEMENT: We put the tags back in so the script works next time!
    replacement = (
        "\n" + 
        html_content + 
        "\n"
    )

    new_readme = re.sub(pattern, replacement, readme)

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(new_readme)

if __name__ == "__main__":
    try:
        stats = get_stats()
        update_readme(stats)
        print("Readme updated successfully!")
    except Exception as e:
        print(f"Error: {e}")
