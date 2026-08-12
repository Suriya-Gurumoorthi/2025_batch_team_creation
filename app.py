import streamlit as st
import pandas as pd
import random
import math
import os

# Programme to Course mapping
programme_to_course = {
    "BBT": "BABIT191",
    "BCL": "BACLE191",
    "BCV": "BACLE191",
    "BCM": "BACHE191",
    "BVD": "BAECE191",
    "BCE": "BACSE191",
    "BBS": "BACSE191",
    "BAI": "BACSE191",
    "BCB": "BACSE191",
    "BDS": "BACSE191",
    "BDE": "BACSE191",
    "BYB": "BACSE191",
    "BIT": "BAITE191",
    "BEE": "BAEEE191",
    "BEI": "BAEEE191",
    "BEC": "BAECE191",
    "BLC": "BAECE191",
    "BHT": "BAHST191",
    "BME": "BAMEE191",
}

# CS group codes
cs_programmes = {"BCE", "BBS", "BAI", "BCB", "BDS", "BDE", "BYB"}


def load_file(file, required_columns=1):
    try:
        df = pd.read_excel(file)
        if len(df.columns) < required_columns:
            st.error(f"File must have at least {required_columns} column(s).")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None


def extract_programme_code(reg_num):
    """Extract first 3 letters (programme code) from registration number"""
    if isinstance(reg_num, str) and len(reg_num) >= 5:
        return reg_num[2:5]  # Assuming format like 25BCE1234
    return None


def is_cs_group(reg_num):
    """Check if registration belongs to CS group."""
    code = extract_programme_code(reg_num)
    return code in cs_programmes


def get_course_code(reg_num):
    """Get the course code for a given registration number"""
    code = extract_programme_code(reg_num)
    return programme_to_course.get(code, "UNKNOWN")


def create_initial_groups(reg_df, reg_col):
    if reg_df is None:
        return None

    if reg_col not in reg_df.columns:
        st.error(
            f"Column '{reg_col}' not found in the file. Available columns: {list(reg_df.columns)}"
        )
        return None

    all_students = reg_df[reg_col].dropna().tolist()
    total_students = len(all_students)
    if total_students < 5:
        st.error("At least 5 students are required to form a team.")
        return None

    expected_teams = math.ceil(total_students / 5)

    # Split CS and non-CS students; within CS, isolate BCE so each team can get one
    bce_students = [s for s in all_students if extract_programme_code(s) == "BCE"]
    other_cs_students = [s for s in all_students if is_cs_group(s) and extract_programme_code(s) != "BCE"]
    cs_students = bce_students + other_cs_students
    other_students = [s for s in all_students if not is_cs_group(s)]
    random.shuffle(bce_students)
    random.shuffle(other_cs_students)
    random.shuffle(other_students)

    remaining_students = cs_students + other_students
    random.shuffle(remaining_students)

    teams = []
    bce_idx = other_cs_idx = other_idx = remain_idx = 0
    assigned_students = set()

    for team_num in range(1, expected_teams + 1):
        team_members = []
        cs_count = 0
        other_count = 0

        # Reserve at least 1 BCE student for this team
        while cs_count < 1 and bce_idx < len(bce_students):
            if bce_students[bce_idx] not in assigned_students:
                student = bce_students[bce_idx]
                team_members.append((student, get_course_code(student)))
                assigned_students.add(student)
                cs_count += 1
            bce_idx += 1

        # Fill remaining CS group quota (up to 3) from other CS codes
        while cs_count < 3 and other_cs_idx < len(other_cs_students):
            if other_cs_students[other_cs_idx] not in assigned_students:
                student = other_cs_students[other_cs_idx]
                team_members.append((student, get_course_code(student)))
                assigned_students.add(student)
                cs_count += 1
            other_cs_idx += 1

        # Add 2 others
        while other_count < 2 and other_idx < len(other_students):
            if other_students[other_idx] not in assigned_students:
                student = other_students[other_idx]
                team_members.append((student, get_course_code(student)))
                assigned_students.add(student)
                other_count += 1
            other_idx += 1

        # Fill remaining slots
        while len(team_members) < 5 and remain_idx < len(remaining_students):
            if remaining_students[remain_idx] not in assigned_students:
                student = remaining_students[remain_idx]
                team_members.append((student, get_course_code(student)))
                assigned_students.add(student)
            remain_idx += 1

        while len(team_members) < 5:
            team_members.append((None, None))

        # Flatten into row: Member1 | CourseCode | Member2 | CourseCode ...
        row = [team_num]
        for student, course in team_members:
            row.append(student)
            row.append(course)

        teams.append(row)

    # Build dataframe with dynamic columns
    columns = ["Team_Number"]
    for i in range(1, 6):
        columns.append(f"Member_{i}")
        columns.append(f"Course_{i}")

    output_df = pd.DataFrame(teams, columns=columns)
    return output_df


def update_groups(new_reg_df, existing_groups_df, reg_col):
    if new_reg_df is None or existing_groups_df is None:
        return None

    if reg_col not in new_reg_df.columns:
        st.error(
            f"Column '{reg_col}' not found in the new registration file. Available columns: {list(new_reg_df.columns)}"
        )
        return None

    new_regs = set(new_reg_df[reg_col].dropna().tolist())
    total_students = len(new_regs)
    expected_teams = math.ceil(total_students / 5)

    # Extract members from existing groups
    existing_members = set()
    member_cols = [c for c in existing_groups_df.columns if c.startswith("Member_")]
    for col in member_cols:
        existing_members.update(existing_groups_df[col].dropna().tolist())

    removed_regs = existing_members - new_regs
    added_regs = new_regs - existing_members

    updated_groups = existing_groups_df.copy()

    # Remove old members
    for col in member_cols:
        updated_groups[col] = updated_groups[col].apply(
            lambda x: None if x in removed_regs else x
        )

    # Adjust team count
    if len(updated_groups) > expected_teams:
        updated_groups = updated_groups[
            updated_groups["Team_Number"] <= expected_teams
        ].copy()
    elif len(updated_groups) < expected_teams:
        new_rows = pd.DataFrame(
            {
                "Team_Number": range(len(updated_groups) + 1, expected_teams + 1),
                **{f"Member_{i}": [None] * (expected_teams - len(updated_groups)) for i in range(1, 6)},
                **{f"Course_{i}": [None] * (expected_teams - len(updated_groups)) for i in range(1, 6)},
            }
        )
        updated_groups = pd.concat([updated_groups, new_rows], ignore_index=True)

    # Assign new students
    assigned_students = set()
    for col in member_cols:
        assigned_students.update(updated_groups[col].dropna().tolist())

    all_students = list(new_regs)
    bce_pool = [s for s in all_students if extract_programme_code(s) == "BCE"]
    other_pool = [s for s in all_students if extract_programme_code(s) != "BCE"]
    random.shuffle(bce_pool)
    random.shuffle(other_pool)

    def team_has_bce(row):
        return any(extract_programme_code(row[col]) == "BCE" for col in member_cols if pd.notnull(row[col]))

    # First pass: give each team without a BCE member one, if a slot and a BCE student are available
    bce_idx = 0
    for idx, row in updated_groups.iterrows():
        if team_has_bce(row):
            continue
        for i in range(1, 6):
            member_col = f"Member_{i}"
            course_col = f"Course_{i}"
            if pd.isnull(updated_groups.at[idx, member_col]) and bce_idx < len(bce_pool):
                student = bce_pool[bce_idx]
                updated_groups.at[idx, member_col] = student
                updated_groups.at[idx, course_col] = get_course_code(student)
                assigned_students.add(student)
                bce_idx += 1
                break

    # Second pass: fill remaining empty slots from whatever's left, order shuffled
    remaining_students = bce_pool[bce_idx:] + other_pool
    random.shuffle(remaining_students)
    student_idx = 0
    for idx, row in updated_groups.iterrows():
        for i in range(1, 6):
            member_col = f"Member_{i}"
            course_col = f"Course_{i}"
            if pd.isnull(updated_groups.at[idx, member_col]) and student_idx < len(remaining_students):
                while student_idx < len(remaining_students) and remaining_students[student_idx] in assigned_students:
                    student_idx += 1
                if student_idx < len(remaining_students):
                    student = remaining_students[student_idx]
                    updated_groups.at[idx, member_col] = student
                    updated_groups.at[idx, course_col] = get_course_code(student)
                    assigned_students.add(student)
                    student_idx += 1

    updated_groups["Team_Number"] = range(1, len(updated_groups) + 1)
    return updated_groups


def save_to_excel(df, filename="team_assignments.xlsx"):
    df.to_excel(filename, index=False)
    with open(filename, "rb") as f:
        st.download_button(
            label="Download Team Assignments",
            data=f,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def main():
    st.title("Team Divider App")

    option = st.radio("Select an option:", ("Group for the first time", "Update existing groups"))

    reg_col = st.text_input("Registration Number Column Name", value="Registration")

    if option == "Group for the first time":
        st.subheader("Upload Registration List")
        reg_file = st.file_uploader("Upload Excel file with registration numbers", type=["xlsx"])

        if reg_file:
            reg_df = load_file(reg_file)
            if reg_df is not None:
                st.write("Available columns in the uploaded file:", list(reg_df.columns))
                if st.button("Create Teams"):
                    output_df = create_initial_groups(reg_df, reg_col=reg_col)
                    if output_df is not None:
                        st.write("Teams created successfully!")
                        st.dataframe(output_df)
                        save_to_excel(output_df)

    else:
        st.subheader("Upload Files")
        new_reg_file = st.file_uploader("Upload new registration list", type=["xlsx"], key="new_reg")
        existing_groups_file = st.file_uploader("Upload existing groups file", type=["xlsx"], key="existing_groups")

        if new_reg_file and existing_groups_file:
            new_reg_df = load_file(new_reg_file)
            existing_groups_df = load_file(existing_groups_file, required_columns=6)
            if new_reg_df is not None and existing_groups_df is not None:
                st.write("Available columns in the new registration file:", list(new_reg_df.columns))
                if st.button("Update Teams"):
                    updated_df = update_groups(new_reg_df, existing_groups_df, reg_col=reg_col)
                    if updated_df is not None:
                        st.write("Teams updated successfully!")
                        st.dataframe(updated_df)
                        save_to_excel(updated_df, "updated_team_assignments.xlsx")


if __name__ == "__main__":
    main()
