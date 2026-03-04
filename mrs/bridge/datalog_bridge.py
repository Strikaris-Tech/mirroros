"""
Mirrors Reasoning Stack - Datalog Bridge
Manages verified facts and pattern queries.

Current: CSV-based storage
Future: DuckDB for recursive Datalog queries
"""

import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

class DatalogBridge:
    """
    Interface for storing and querying verified facts.

    Schema: predicate | subject | object | timestamp | verified_by

    Future Migration Path:
    - Phase 1 (current): CSV with pandas queries
    - Phase 2: DuckDB with SQL + recursive CTEs
    - Phase 3: Native Datalog engine (Souffle/DDlog)
    """

    def __init__(
        self,
        facts_path: str = "memory/verified_facts.csv",
        use_duckdb: bool = False
    ):
        self.facts_path = Path(facts_path)
        self.use_duckdb = use_duckdb
        self._ensure_schema()

        if use_duckdb:
            self._init_duckdb()

    def _ensure_schema(self):
        """Create CSV with proper schema if it doesn't exist"""
        if not self.facts_path.exists():
            self.facts_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.facts_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'predicate',
                    'subject',
                    'object',
                    'timestamp',
                    'verified_by'
                ])

    def _init_duckdb(self):
        """Initialize DuckDB connection (future enhancement)"""
        try:
            import duckdb
            db_path = self.facts_path.with_suffix('.duckdb')
            self.db = duckdb.connect(str(db_path))

            # Create table
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    predicate VARCHAR,
                    subject VARCHAR,
                    object VARCHAR,
                    timestamp TIMESTAMP,
                    verified_by VARCHAR
                )
            """)
        except ImportError:
            raise ImportError(
                "DuckDB not installed. Install with: pip install duckdb"
            )

    def store_fact(
        self,
        predicate: str,
        subject: str,
        obj: str,
        verified_by: str = "mrs"
    ) -> Dict[str, Any]:
        """
        Store a verified fact.

        Args:
            predicate: Fact type (e.g., "code_review", "memory_access")
            subject: Subject of fact (e.g., "ledgerlark", "pr_123")
            obj: Object/value (e.g., "approved", "audit_log")
            verified_by: Verification source

        Returns:
            Status dict
        """
        timestamp = datetime.now().isoformat()

        if self.use_duckdb:
            return self._store_fact_duckdb(predicate, subject, obj, timestamp, verified_by)
        else:
            return self._store_fact_csv(predicate, subject, obj, timestamp, verified_by)

    def _store_fact_csv(
        self,
        predicate: str,
        subject: str,
        obj: str,
        timestamp: str,
        verified_by: str
    ) -> Dict[str, Any]:
        """Store fact in CSV"""
        with open(self.facts_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([predicate, subject, obj, timestamp, verified_by])

        return {
            "success": True,
            "predicate": predicate,
            "timestamp": timestamp
        }

    def _store_fact_duckdb(
        self,
        predicate: str,
        subject: str,
        obj: str,
        timestamp: str,
        verified_by: str
    ) -> Dict[str, Any]:
        """Store fact in DuckDB"""
        self.db.execute(
            "INSERT INTO facts VALUES (?, ?, ?, ?, ?)",
            [predicate, subject, obj, timestamp, verified_by]
        )
        return {
            "success": True,
            "predicate": predicate,
            "timestamp": timestamp
        }

    def query_facts(
        self,
        predicate: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query stored facts with optional filters.

        Args:
            predicate: Filter by predicate type
            subject: Filter by subject
            limit: Max results

        Returns:
            List of matching facts
        """
        if self.use_duckdb:
            return self._query_facts_duckdb(predicate, subject, limit)
        else:
            return self._query_facts_csv(predicate, subject, limit)

    def _query_facts_csv(
        self,
        predicate: Optional[str],
        subject: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Query facts from CSV using pandas"""
        if not self.facts_path.exists():
            return []

        df = pd.read_csv(self.facts_path)

        # Apply filters
        if predicate:
            df = df[df['predicate'] == predicate]
        if subject:
            df = df[df['subject'] == subject]

        # Limit results
        df = df.head(limit)

        return df.to_dict('records')

    def _query_facts_duckdb(
        self,
        predicate: Optional[str],
        subject: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Query facts from DuckDB"""
        query = "SELECT * FROM facts WHERE 1=1"
        params = []

        if predicate:
            query += " AND predicate = ?"
            params.append(predicate)
        if subject:
            query += " AND subject = ?"
            params.append(subject)

        query += f" LIMIT {limit}"

        result = self.db.execute(query, params).fetchdf()
        return result.to_dict('records')

    def recursive_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute recursive Datalog-style query.

        Requires DuckDB mode (uses recursive CTEs).

        Example:
            WITH RECURSIVE ancestors AS (
                SELECT subject, object FROM facts WHERE predicate = 'parent'
                UNION
                SELECT a.subject, f.object
                FROM ancestors a
                JOIN facts f ON a.object = f.subject
                WHERE f.predicate = 'parent'
            )
            SELECT * FROM ancestors
        """
        if not self.use_duckdb:
            raise NotImplementedError(
                "Recursive queries require DuckDB. Initialize with use_duckdb=True"
            )

        result = self.db.execute(query).fetchdf()
        return result.to_dict('records')

    def export_to_prolog(self, output_path: str):
        """
        Export facts as Prolog predicates.

        Args:
            output_path: Path to output .pl file
        """
        facts = self.query_facts()

        with open(output_path, 'w') as f:
            f.write("% Auto-generated from verified facts\n")
            f.write(f"% Generated: {datetime.now().isoformat()}\n\n")

            for fact in facts:
                # Format as Prolog fact
                pred = fact['predicate']
                subj = fact['subject']
                obj = fact['object']
                f.write(f"{pred}({subj}, {obj}).\n")

    def import_from_prolog(self, prolog_file: str):
        """
        Import facts from a Prolog file.

        Parses simple facts of form: predicate(subject, object).
        """
        import re

        fact_pattern = re.compile(r'(\w+)\((\w+),\s*(\w+)\)\.')

        with open(prolog_file) as f:
            for line in f:
                match = fact_pattern.match(line.strip())
                if match:
                    pred, subj, obj = match.groups()
                    self.store_fact(pred, subj, obj, verified_by="import")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored facts"""
        facts = self.query_facts()

        if not facts:
            return {"total_facts": 0}

        df = pd.DataFrame(facts)

        return {
            "total_facts": len(df),
            "predicates": df['predicate'].nunique(),
            "predicate_counts": df['predicate'].value_counts().to_dict(),
            "oldest_fact": df['timestamp'].min(),
            "newest_fact": df['timestamp'].max()
        }
