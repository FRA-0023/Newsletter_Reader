import email.utils
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
from notion_client import Client

from src.core.schemas import (
    QuantitativeMetricsPayload,
    JournalisticEditorialPayload,
    BusinessFrameworkPayload,
    DailyBriefingOutput,
)

logger = logging.getLogger(__name__)


class NotionClientAdapter:
    def __init__(self, token: str):
        if not token:
            raise ValueError("NOTION_TOKEN must be provided.")
        self.client = Client(auth=token)

    def save_page(
        self,
        database_id: str,
        subject: str,
        date_str: str,
        layout_type: str,
        notion_data: Any,
    ) -> str:
        if not database_id:
            raise ValueError("Database ID must not be empty.")

        iso_date = self._parse_date_to_iso(date_str)
        blocks: List[Dict[str, Any]] = []
        page_title = subject.strip()

        if layout_type == "bullet_metrics":
            page_title, blocks = self._build_bullet_metrics(subject, notion_data)
        elif layout_type == "editorial_sections":
            page_title, blocks = self._build_editorial_sections(subject, notion_data)
        elif layout_type == "framework_table":
            page_title, blocks = self._build_framework_table(subject, notion_data)
        else:
            raise ValueError(f"Unknown Notion layout_type: {layout_type}")

        logger.info(f"Creating Notion page in DB {database_id[:8]}... with {len(blocks)} blocks")

        response = self.client.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {
                    "title": [{"text": {"content": page_title[:100]}}]
                },
                "Received": {
                    "date": {"start": iso_date}
                },
            },
            children=blocks[:100],  # Notion accepts up to 100 children in create
        )

        page_id = response.get("id", "")
        logger.info(f"Notion page created successfully. ID: {page_id}")
        return page_id

    def _parse_date_to_iso(self, date_str: str) -> str:
        try:
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            return datetime.utcnow().strftime("%Y-%m-%d")

    def _build_bullet_metrics(
        self, fallback_title: str, data: QuantitativeMetricsPayload
    ) -> tuple[str, List[Dict[str, Any]]]:
        title = f"{data.macro_topic}: {fallback_title}"
        blocks: List[Dict[str, Any]] = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": data.macro_topic[:2000]}}]
                },
            }
        ]

        for pt in data.data_points:
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": pt[:2000]}}]
                    },
                }
            )

        return title, blocks

    def _build_editorial_sections(
        self, fallback_title: str, data: JournalisticEditorialPayload
    ) -> tuple[str, List[Dict[str, Any]]]:
        title = data.headline or fallback_title
        blocks: List[Dict[str, Any]] = []

        sections = [
            data.section_whale,
            data.section_focus,
            data.section_technical,
        ]

        for sec in sections:
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": sec.title[:2000]}}]
                    },
                }
            )
            for line in sec.body_lines:
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                        },
                    }
                )

        # Bottom line
        if data.bottom_line:
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "🎯 Bottom Line"}}]
                    },
                }
            )
            for bl_line in data.bottom_line:
                blocks.append(
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "icon": {"emoji": "📌"},
                            "rich_text": [{"type": "text", "text": {"content": bl_line[:2000]}}],
                        },
                    }
                )

        return title, blocks

    def _build_framework_table(
        self, fallback_title: str, data: BusinessFrameworkPayload
    ) -> tuple[str, List[Dict[str, Any]]]:
        title = data.punchy_title or fallback_title
        blocks: List[Dict[str, Any]] = []

        if data.intro:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": data.intro[:2000]}}]
                    },
                }
            )

        # Core Principle
        blocks.append(
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "💡 The Core Principle"}}]
                },
            }
        )
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": data.core_principle[:2000]}}]
                },
            }
        )

        # Framework Steps
        if data.framework_steps:
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "🛠️ The Framework / Method"}}]
                    },
                }
            )
            for step in data.framework_steps:
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": step[:2000]}}]
                        },
                    }
                )

        # Strategy Table
        if data.strategy_table:
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "📊 Strategy & Application"}}]
                    },
                }
            )
            # Create table block
            table_rows = [
                {
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": "Scenario"}}],
                            [{"type": "text", "text": {"content": "Strategic Move"}}],
                        ]
                    },
                }
            ]
            for row in data.strategy_table:
                table_rows.append(
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": row.scenario[:1000]}}],
                                [{"type": "text", "text": {"content": row.strategic_move[:1000]}}],
                            ]
                        },
                    }
                )
            blocks.append(
                {
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": 2,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": table_rows[:90],
                    },
                }
            )

        # Case Lesson
        if data.case_lesson:
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "🧠 The Lesson"}}]
                    },
                }
            )
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": data.case_lesson[:2000]}}]
                    },
                }
            )

        # Bottom Line
        if data.bottom_line:
            blocks.append(
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "icon": {"emoji": "🎯"},
                        "rich_text": [{"type": "text", "text": {"content": data.bottom_line[:2000]}}],
                    },
                }
            )

        return title, blocks

    def save_daily_briefing_page(
        self,
        database_id: str,
        date_str: str,
        data: DailyBriefingOutput,
        language: str = "en",
    ) -> str:
        """
        Creates a consolidated executive briefing page in the user's dedicated Daily Briefings Notion database.
        
        Trade-off: Rather than flattening the daily summary into raw text, we generate structured Notion blocks
        (overview callout, thematic domain headings, key takeaway bullets, and direct back-links to each
        underlying newsletter page). This elevates Notion into an interactive executive knowledge repository.
        """
        if not database_id:
            raise ValueError("Database ID must not be empty.")

        iso_date = self._parse_date_to_iso(date_str)
        is_it = language.lower() == "it"

        blocks: List[Dict[str, Any]] = []

        # 1. Macro Overview Callout Block
        overview_title = "Panoramica in Breve: " if is_it else "Executive Overview: "
        blocks.append(
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "☕"},
                    "color": "blue_background",
                    "rich_text": [
                        {"type": "text", "text": {"content": overview_title, "annotations": {"bold": True}}},
                        {"type": "text", "text": {"content": data.macro_narrative[:1800]}},
                    ],
                },
            }
        )

        # 2. Section Heading
        section_heading = "I Punti Salienti di Oggi" if is_it else "Today's Intelligence Breakdown"
        blocks.append(
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": section_heading}}],
                },
            }
        )

        # 3. Domain Cards
        for d in data.domain_breakdowns:
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": d.domain_name}}],
                    },
                }
            )
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": d.core_thesis[:2000], "annotations": {"italic": True}}}
                        ],
                    },
                }
            )
            for bullet in d.key_takeaways:
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": bullet[:2000]}}],
                        },
                    }
                )
            if d.notion_url:
                link_text = "🔗 Apri approfondimento completo su Notion" if is_it else "🔗 Open full deep-dive note in Notion"
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": link_text, "link": {"url": d.notion_url}},
                                }
                            ],
                        },
                    }
                )

        # 4. Actionable Priority Callout
        priority_label = "🎯 Spunto per Domani: " if is_it else "🎯 Actionable Priority for Tomorrow: "
        blocks.append(
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "🎯"},
                    "color": "green_background",
                    "rich_text": [
                        {"type": "text", "text": {"content": priority_label, "annotations": {"bold": True}}},
                        {"type": "text", "text": {"content": data.actionable_priority[:1800]}},
                    ],
                },
            }
        )

        logger.info(f"Creating Notion Daily Briefing page in DB {database_id[:8]}... with {len(blocks)} blocks")

        response = self.client.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {
                    "title": [{"text": {"content": data.executive_title[:100]}}]
                },
                "Received": {
                    "date": {"start": iso_date}
                },
            },
            children=blocks[:100],
        )

        page_id = response.get("id", "")
        logger.info(f"Notion Daily Briefing page successfully created with ID: {page_id}")
        return page_id
