"""
Migration: Add SECM (Structural-Epistemic Coding Matrix) columns to bias_ratings table.

This migration adds 25 new columns to support the SECM bias analysis system:
- 12 ideological binary variables (6 left markers + 6 right markers)
- 10 epistemic binary variables (5 high integrity + 5 low integrity)
- 2 computed scores (ideological_score, epistemic_score)
- 1 reasoning JSON storage column

All columns are nullable to support gradual migration and backward compatibility.
"""

import sqlite3


def run_migration(db_path: str = "veritas_news.db") -> bool:
    """
    Add SECM columns to bias_ratings table.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        True if migration successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if migration already applied
        cursor.execute("PRAGMA table_info(bias_ratings)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Ideological Left Markers (6 columns)
        ideological_left_columns = [
            ("secm_ideol_l1_systemic_naming", "INTEGER"),
            ("secm_ideol_l2_power_gap_lexicon", "INTEGER"),
            ("secm_ideol_l3_elite_culpability", "INTEGER"),
            ("secm_ideol_l4_resource_redistribution", "INTEGER"),
            ("secm_ideol_l5_change_as_justice", "INTEGER"),
            ("secm_ideol_l6_care_harm", "INTEGER"),
        ]
        
        # Ideological Right Markers (6 columns)
        ideological_right_columns = [
            ("secm_ideol_r1_agentic_culpability", "INTEGER"),
            ("secm_ideol_r2_order_lexicon", "INTEGER"),
            ("secm_ideol_r3_institutional_defense", "INTEGER"),
            ("secm_ideol_r4_meritocratic_defense", "INTEGER"),
            ("secm_ideol_r5_change_as_threat", "INTEGER"),
            ("secm_ideol_r6_sanctity_degradation", "INTEGER"),
        ]
        
        # Epistemic High Integrity Markers (5 columns)
        epistemic_high_columns = [
            ("secm_epist_h1_primary_documentation", "INTEGER"),
            ("secm_epist_h2_adversarial_sourcing", "INTEGER"),
            ("secm_epist_h3_specific_attribution", "INTEGER"),
            ("secm_epist_h4_data_contextualization", "INTEGER"),
            ("secm_epist_h5_methodological_transparency", "INTEGER"),
        ]
        
        # Epistemic Low Integrity Markers (5 columns)
        epistemic_low_columns = [
            ("secm_epist_e1_emotive_adjectives", "INTEGER"),
            ("secm_epist_e2_labeling_othering", "INTEGER"),
            ("secm_epist_e3_causal_certainty", "INTEGER"),
            ("secm_epist_e4_imperative_direct_address", "INTEGER"),
            ("secm_epist_e5_motivated_reasoning", "INTEGER"),
        ]
        
        # Computed Scores (2 columns)
        score_columns = [
            ("secm_ideological_score", "REAL"),
            ("secm_epistemic_score", "REAL"),
        ]
        
        # Reasoning Storage (1 column)
        reasoning_columns = [
            ("secm_reasoning_json", "TEXT"),
        ]
        
        # Combine all columns
        all_columns = (
            ideological_left_columns +
            ideological_right_columns +
            epistemic_high_columns +
            epistemic_low_columns +
            score_columns +
            reasoning_columns
        )
        
        # Add columns that don't exist
        added_count = 0
        for column_name, column_type in all_columns:
            if column_name not in columns:
                print(f"Adding column {column_name} to bias_ratings table")
                cursor.execute(
                    f"ALTER TABLE bias_ratings ADD COLUMN {column_name} {column_type}"
                )
                added_count += 1
            else:
                print(f"Column {column_name} already exists, skipping")
        
        conn.commit()
        conn.close()
        
        if added_count > 0:
            print(f"✓ SECM migration completed successfully ({added_count} columns added)")
        else:
            print("✓ SECM migration: all columns already exist")
        return True
        
    except Exception as e:
        print(f"✗ SECM migration failed: {e}")
        return False


if __name__ == "__main__":
    # Run migration on default database
    run_migration()



