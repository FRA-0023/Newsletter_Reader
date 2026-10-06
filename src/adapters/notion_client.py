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
        self._schema_cache: Dict[str, tuple[str, Optional[str]]] = {}

    def _resolve_db_schema(self, database_id: str) -> tuple[str, Optional[str]]:
        """
        Resolves the title property name and date property name for a Notion database.
        Returns (title_prop_name, date_prop_name).
        Caches results per database_id to avoid redundant network calls.
        """
        # Cache schema as (title_prop, date_prop, props)
        if database_id in self._schema_cache:
            return self._schema_cache[database_id]

        title_prop = "Name"
        date_prop = "Received"
        props = {}

        try:
            db = self.client.databases.retrieve(database_id=database_id)
            props = db.get("properties")
            if not props:
                ds = db.get("data_sources", [])
                if ds:
                    ds_data = self.client.request(path=f"data_sources/{ds[0]['id']}", method="GET")
                    props = ds_data.get("properties", {})

            if props:
                found_title = next(
                    (k for k, v in props.items() if isinstance(v, dict) and v.get("type") == "title"),
                    None,
                )
                if found_title:
                    title_prop = found_title
                found_date = next(
                    (k for k, v in props.items() if isinstance(v, dict) and v.get("type") == "date"),
                    None,
                )
                date_prop = found_date
        except Exception as e:
            logger.warning(
                f"Could not inspect schema for database {database_id}: {e}. Falling back to default properties."
            )

        self._schema_cache[database_id] = (title_prop, date_prop, props or {})
        return title_prop, date_prop, props or {}

    def save_page(
        self,
        database_id: str,
        subject: str,
        date_str: str,
        layout_type: str,
        notion_data: Any,
        domain_id: Optional[str] = None,
    ) -> str:
        if not database_id:
            raise ValueError("Database ID must not be empty.")

        iso_date = self._parse_date_to_iso(date_str)
        blocks: List[Dict[str, Any]] = []
        page_title = subject.strip()

        # ARCHITETTURA: Gestione della formattazione specifica per dominio.
        # Mozi Minute adotta storicamente il prefisso iconico '👃🏻 ' e rimuove 'Mozi Minute: '
        # per preservare la leggibilità e la consistenza visiva nel database Notion 'Mozi Advices'.
        is_mozi = (domain_id == "mozi_minute") or ("Mozi Minute:" in subject)

        if layout_type == "bullet_metrics":
            page_title, blocks = self._build_bullet_metrics(subject, notion_data)
        elif layout_type == "editorial_sections":
            page_title, blocks = self._build_editorial_sections(subject, notion_data)
        elif layout_type == "framework_table":
            built_title, blocks = self._build_framework_table(subject, notion_data)
            if is_mozi:
                clean_name = (getattr(notion_data, "punchy_title", None) or subject).replace("Mozi Minute: ", "").strip()
                page_title = f"👃🏻 {clean_name}"
            else:
                page_title = built_title
        else:
            raise ValueError(f"Unknown Notion layout_type: {layout_type}")

        title_prop, date_prop, db_props = self._resolve_db_schema(database_id)
        properties: Dict[str, Any] = {
            title_prop: {
                "title": [{"text": {"content": page_title[:100]}}]
            }
        }
        if date_prop:
            properties[date_prop] = {
                "date": {"start": iso_date}
            }

        # ARCHITETTURA: Popolamento difensivo delle colonne tassonomiche di Notion.
        # 1. Colonna 'Format' (status): se presente nel database, seleziona l'opzione coerente (es. 'Mozi Minute').
        if "Format" in db_props and db_props["Format"].get("type") == "status":
            fmt_options = [o.get("name") for o in db_props["Format"].get("status", {}).get("options", [])]
            if is_mozi and "Mozi Minute" in fmt_options:
                properties["Format"] = {"status": {"name": "Mozi Minute"}}

        # 2. Colonna 'Content' (select): assegna la categoria estratta (es. 'Mentality', 'Sales', 'Strategy')
        if "Content" in db_props and db_props["Content"].get("type") == "select":
            category = getattr(notion_data, "category", None)
            if category:
                valid_opts = [o.get("name") for o in db_props["Content"].get("select", {}).get("options", [])]
                matched_opt = next((opt for opt in valid_opts if opt.lower() == category.lower()), None)
                if matched_opt:
                    properties["Content"] = {"select": {"name": matched_opt}}
                elif valid_opts:
                    logger.warning(f"Category '{category}' non tra le opzioni valide {valid_opts}. Fallback su '{valid_opts[0]}'.")
                    properties["Content"] = {"select": {"name": valid_opts[0]}}

        logger.info(f"Creating Notion page in DB {database_id[:8]}... with {len(blocks)} blocks (props: {list(properties.keys())})")

        response = self.client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
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
        # ARCHITETTURA: Allineiamo la nomenclatura del blocco callout di Notion a 'Radar Esecutivo',
        # rispecchiando l'eliminazione delle narrazioni olistiche artificiali.
        overview_title = "Radar Esecutivo: " if is_it else "Executive Radar: "
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

        title_prop, date_prop = self._resolve_db_schema(database_id)
        properties: Dict[str, Any] = {
            title_prop: {
                "title": [{"text": {"content": data.executive_title[:100]}}]
            }
        }
        if date_prop:
            properties[date_prop] = {
                "date": {"start": iso_date}
            }

        response = self.client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=blocks[:100],
        )

        page_id = response.get("id", "")
        logger.info(f"Notion Daily Briefing page successfully created with ID: {page_id}")
        return page_id
