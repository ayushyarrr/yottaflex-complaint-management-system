from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models import Team, Agent


TEAM_DATA = [
    {
        "team_name": "Delivery Support",
        "description": "Handles delivery delays, missing items, and cancellation complaints.",
        "agents": [
            "Aarav Sharma",
            "Priya Verma",
            "Rohan Mehta",
        ],
    },
    {
        "team_name": "Finance Support",
        "description": "Handles payment, billing, and refund complaints.",
        "agents": [
            "Ananya Gupta",
            "Karan Malhotra",
            "Neha Singh",
        ],
    },
    {
        "team_name": "Product Support",
        "description": "Handles damaged products, defects, warranty, and replacements.",
        "agents": [
            "Ishita Rao",
            "Arjun Kapoor",
            "Meera Joshi",
        ],
    },
    {
        "team_name": "Safety Response",
        "description": "Handles product safety risks and urgent safety-related complaints.",
        "agents": [
            "Vikram Nair",
            "Sana Khan",
        ],
    },
    {
        "team_name": "General Support",
        "description": "Handles account-related and uncategorized complaints.",
        "agents": [
            "Dev Patel",
            "Riya Das",
            "Kabir Shah",
        ],
    },
]


def generate_teams_and_agents():
    db = SessionLocal()

    try:
        existing_teams = db.query(Team).count()
        existing_agents = db.query(Agent).count()

        if existing_teams > 0 or existing_agents > 0:
            print("Team or agent records already exist.")
            print("No records were added to avoid duplicates.")
            print(f"Existing teams: {existing_teams}")
            print(f"Existing agents: {existing_agents}")
            return

        total_agents = 0

        for team_info in TEAM_DATA:
            team = Team(
                team_name=team_info["team_name"],
                description=team_info["description"],
                is_active=True,
            )

            db.add(team)
            db.flush()

            for agent_name in team_info["agents"]:
                agent = Agent(
                    agent_name=agent_name,
                    team_id=team.team_id,
                    workload_capacity=200,
                    is_active=True,
                )

                db.add(agent)
                total_agents += 1

        db.commit()

        print("Team and agent generation completed successfully.")
        print(f"Teams created: {len(TEAM_DATA)}")
        print(f"Agents created: {total_agents}")

        for team_info in TEAM_DATA:
            print(f"- {team_info['team_name']}: {len(team_info['agents'])} agents")

    except SQLAlchemyError:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_teams_and_agents()