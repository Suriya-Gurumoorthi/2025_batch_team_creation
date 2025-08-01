import streamlit as st
import pandas as pd
import random
import math
import os

def load_file(file, required_columns=1):
    """Load and validate an uploaded Excel file."""
    try:
        df = pd.read_excel(file)
        if len(df.columns) < required_columns:
            st.error(f"File must have at least {required_columns} column(s).")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def is_bce_reg(reg_num):
    """Check if a registration number belongs to BCE batch."""
    return isinstance(reg_num, str) and reg_num.startswith('25BCE')

def create_initial_groups(reg_df, reg_col):
    """Create initial team groupings, prioritizing 3 BCE and 2 others per team."""
    if reg_df is None:
        return None
    
    # Validate column name
    if reg_col not in reg_df.columns:
        st.error(f"Column '{reg_col}' not found in the file. Available columns: {list(reg_df.columns)}")
        return None
    
    # Get all students
    all_students = reg_df[reg_col].dropna().tolist()
    total_students = len(all_students)
    if total_students < 5:
        st.error("At least 5 students are required to form a team.")
        return None
    
    # Calculate expected teams
    expected_teams = math.ceil(total_students / 5)
    
    # Separate BCE and non-BCE students
    bce_students = [s for s in all_students if is_bce_reg(s)]
    other_students = [s for s in all_students if not is_bce_reg(s)]
    random.shuffle(bce_students)
    random.shuffle(other_students)
    
    # Combine remaining students for flexible assignment
    remaining_students = bce_students + other_students
    random.shuffle(remaining_students)  # Shuffle for randomness
    
    # Create teams
    teams = []
    bce_idx = other_idx = remain_idx = 0
    assigned_students = set()
    
    for team_num in range(1, expected_teams + 1):
        team = [team_num]
        team_members = []
        bce_count = 0
        other_count = 0
        
        # Try to add 3 BCE students
        while bce_count < 3 and bce_idx < len(bce_students):
            if bce_students[bce_idx] not in assigned_students:
                team_members.append(bce_students[bce_idx])
                assigned_students.add(bce_students[bce_idx])
                bce_count += 1
            bce_idx += 1
        
        # Try to add 2 non-BCE students
        while other_count < 2 and other_idx < len(other_students):
            if other_students[other_idx] not in assigned_students:
                team_members.append(other_students[other_idx])
                assigned_students.add(other_students[other_idx])
                other_count += 1
            other_idx += 1
        
        # Fill remaining slots with any students
        while len(team_members) < 5 and remain_idx < len(remaining_students):
            if remaining_students[remain_idx] not in assigned_students:
                team_members.append(remaining_students[remain_idx])
                assigned_students.add(remaining_students[remain_idx])
            remain_idx += 1
        
        # Pad with None if team is incomplete (last team may have < 5)
        while len(team_members) < 5:
            team_members.append(None)
        
        # Add team to list
        team.extend(team_members)
        teams.append(team)
        
        # Warn if team composition deviates significantly
        if len(team_members) < 5:
            st.warning(f"Team {team_num} has {len(team_members)} members.")
        elif bce_count != 3 or other_count != 2:
            st.warning(f"Team {team_num} has {bce_count} BCE and {other_count} others.")
    
    # Create output DataFrame
    output_df = pd.DataFrame(teams, columns=['Team_Number', 'Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5'])
    
    # Check for duplicates
    all_members = [m for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5'] for m in output_df[col].dropna()]
    if len(all_members) != len(set(all_members)):
        st.error("Duplicate students found in teams. Please check the input file.")
        return None
    
    return output_df

def update_groups(new_reg_df, existing_groups_df, reg_col):
    """Update existing groups based on new registration list."""
    if new_reg_df is None or existing_groups_df is None:
        return None
    
    # Validate column name
    if reg_col not in new_reg_df.columns:
        st.error(f"Column '{reg_col}' not found in the new registration file. Available columns: {list(new_reg_df.columns)}")
        return None
    
    # Get new registration numbers
    new_regs = set(new_reg_df[reg_col].dropna().tolist())
    total_students = len(new_regs)
    expected_teams = math.ceil(total_students / 5)
    
    # Get existing members
    existing_members = set()
    for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5']:
        existing_members.update(existing_groups_df[col].dropna().tolist())
    
    # Identify added and removed registrations
    removed_regs = existing_members - new_regs
    added_regs = new_regs - existing_members
    
    # Create updated groups
    updated_groups = existing_groups_df.copy()
    
    # Remove registrations that are no longer in the list
    for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5']:
        updated_groups[col] = updated_groups[col].apply(lambda x: None if x in removed_regs else x)
    
    # Truncate or extend teams to match expected count
    if len(updated_groups) > expected_teams:
        updated_groups = updated_groups[updated_groups['Team_Number'] <= expected_teams].copy()
    elif len(updated_groups) < expected_teams:
        new_rows = pd.DataFrame({
            'Team_Number': range(len(updated_groups) + 1, expected_teams + 1),
            'Member_1': [None] * (expected_teams - len(updated_groups)),
            'Member_2': [None] * (expected_teams - len(updated_groups)),
            'Member_3': [None] * (expected_teams - len(updated_groups)),
            'Member_4': [None] * (expected_teams - len(updated_groups)),
            'Member_5': [None] * (expected_teams - len(updated_groups))
        })
        updated_groups = pd.concat([updated_groups, new_rows], ignore_index=True)
    
    # Get all available students for assignment
    all_students = list(new_regs)
    random.shuffle(all_students)
    
    # Track assigned students
    assigned_students = set()
    for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5']:
        assigned_students.update(updated_groups[col].dropna().tolist())
    
    student_idx = 0
    for idx, row in updated_groups.iterrows():
        team_members = [row[col] for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5'] if pd.notnull(row[col])]
        bce_count = sum(1 for m in team_members if is_bce_reg(m))
        other_count = len(team_members) - bce_count
        
        # Fill empty slots with any available student
        for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5']:
            if pd.isnull(row[col]) and student_idx < len(all_students):
                while student_idx < len(all_students) and all_students[student_idx] in assigned_students:
                    student_idx += 1
                if student_idx < len(all_students):
                    updated_groups.at[idx, col] = all_students[student_idx]
                    assigned_students.add(all_students[student_idx])
                    student_idx += 1
        
        # Check team composition
        team_size = sum(1 for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5'] if pd.notnull(updated_groups.loc[idx, col]))
        new_bce_count = sum(1 for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5'] if pd.notnull(updated_groups.loc[idx, col]) and is_bce_reg(updated_groups.loc[idx, col]))
        new_other_count = team_size - new_bce_count
        if team_size < 5:
            st.warning(f"Team {row['Team_Number']} has {team_size} members after update.")
        elif new_bce_count != 3 or new_other_count != 2:
            st.warning(f"Team {row['Team_Number']} has {new_bce_count} BCE and {new_other_count} others.")
    
    # Reset team numbers
    updated_groups['Team_Number'] = range(1, len(updated_groups) + 1)
    
    # Check for duplicates
    all_members = [m for col in ['Member_1', 'Member_2', 'Member_3', 'Member_4', 'Member_5'] for m in updated_groups[col].dropna()]
    if len(all_members) != len(set(all_members)):
        st.error("Duplicate students found in teams. Please check the input files.")
        return None
    
    return updated_groups

def save_to_excel(df, filename='team_assignments.xlsx'):
    """Save DataFrame to Excel and provide download link."""
    df.to_excel(filename, index=False)
    with open(filename, 'rb') as f:
        st.download_button(
            label="Download Team Assignments",
            data=f,
            file_name=filename,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

def main():
    st.title("Team Divider App")
    
    # Option selection
    option = st.radio("Select an option:", ("Group for the first time", "Update existing groups"))
    
    # Input for registration column name
    st.subheader("Specify Column Name")
    reg_col = st.text_input("Registration Number Column Name", value="Registration")
    
    if option == "Group for the first time":
        st.subheader("Upload Registration List")
        reg_file = st.file_uploader("Upload Excel file with registration numbers", type=['xlsx'])
        
        if reg_file:
            reg_df = load_file(reg_file)
            if reg_df is not None:
                # Display available columns
                st.write("Available columns in the uploaded file:", list(reg_df.columns))
                if st.button("Create Teams"):
                    output_df = create_initial_groups(reg_df, reg_col=reg_col)
                    if output_df is not None:
                        st.write("Teams created successfully!")
                        st.dataframe(output_df)
                        save_to_excel(output_df)
    
    else:  # Update existing groups
        st.subheader("Upload Files")
        new_reg_file = st.file_uploader("Upload new registration list", type=['xlsx'], key='new_reg')
        existing_groups_file = st.file_uploader("Upload existing groups file", type=['xlsx'], key='existing_groups')
        
        if new_reg_file and existing_groups_file:
            new_reg_df = load_file(new_reg_file)
            existing_groups_df = load_file(existing_groups_file, required_columns=6)
            if new_reg_df is not None and existing_groups_df is not None:
                # Display available columns in new registration file
                st.write("Available columns in the new registration file:", list(new_reg_df.columns))
                if st.button("Update Teams"):
                    updated_df = update_groups(new_reg_df, existing_groups_df, reg_col=reg_col)
                    if updated_df is not None:
                        st.write("Teams updated successfully!")
                        st.dataframe(updated_df)
                        save_to_excel(updated_df, 'updated_team_assignments.xlsx')

if __name__ == "__main__":
    main()