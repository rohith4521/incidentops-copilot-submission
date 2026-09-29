"""CLI tool to seed realistic historical SRE incidents directly into Hindsight Continuous Memory.

Adheres strictly to Invariant 2: Direct Hindsight API calls, zero mock storage.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.models.memory import MemorySourceType, MemoryStatus, RetainIncidentPayload
from app.services.hindsight_service import hindsight_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_hindsight")


async def main():
    logger.info("Connecting to Hindsight API at '%s'...", settings.hindsight_api_url)
    logger.info("Target Memory Bank: '%s'", settings.hindsight_bank_id)

    # Check health
    health = await hindsight_service.check_health()
    logger.info("Health Check Status: %s", health)

    if health.get("status") == "unauthorized":
        logger.error(
            "Authentication required by Hindsight Cloud. Please set HINDSIGHT_API_KEY in .env before running this script."
        )
        sys.exit(1)
    elif health.get("status") in ["unreachable", "error"]:
        logger.error("Hindsight API is unreachable at %s: %s", settings.hindsight_api_url, health.get("error"))
        sys.exit(1)

    seed_file = PROJECT_ROOT / "app" / "data" / "seed_incidents.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        incidents = json.load(f)

    logger.info("Found %d historical SRE incidents to retain into Hindsight...", len(incidents))

    for inc in incidents:
        logger.info("Retaining %s (%s - %s)...", inc["incident_id"], inc["service"], inc["title"])
        payload = RetainIncidentPayload(
            bank_id=settings.hindsight_bank_id,
            incident_id=inc["incident_id"],
            service=inc["service"],
            severity=inc.get("severity", "HIGH"),
            alert_signature=inc.get("alert_signature", f"AlertSignature-{inc['service']}"),
            title=inc.get("title", f"{inc['incident_id']} - {inc['service']}"),
            symptoms=inc.get("symptoms", []),
            root_cause=inc["root_cause"],
            failed_mitigations=inc.get("failed_mitigations", []),
            verified_runbook=inc.get("verified_runbook") or inc.get("runbook_executed", "None"),
            postmortem_summary=inc.get("postmortem_summary") or inc.get("resolution", ""),
            resolution=inc.get("resolution"),
            runbook_executed=inc.get("runbook_executed"),
            timeline=inc.get("timeline"),
            lessons_learned=inc.get("preventative_actions"),
            tags=inc.get("tags", []),
            memory_status=MemoryStatus.VERIFIED,
            source_type=MemorySourceType.HUMAN_VERIFIED,
            verified_by="sre-core-team",
            source_incident_id=inc["incident_id"],
        )
        
        success = False
        for attempt in range(5):
            res = await hindsight_service.retain_incident(payload)
            if res.get("success"):
                logger.info("  [SUCCESS] Retained %s into Hindsight bank '%s'", inc["incident_id"], settings.hindsight_bank_id)
                success = True
                break
            else:
                logger.warning("  [RETRY %d/5] Failed retaining %s: %s. Retrying in 1.5s...", attempt + 1, inc["incident_id"], res.get("error"))
                await asyncio.sleep(1.5)

        if not success:
            logger.error("  [FAILED] Could not retain %s after retries.", inc["incident_id"])

        await asyncio.sleep(0.5)

    logger.info("Memory seeding procedure completed.")


if __name__ == "__main__":
    asyncio.run(main())
