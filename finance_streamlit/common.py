from datetime import datetime
import streamlit as st
class DatabaseOperation:
    def __init__(self, operation_time: datetime, operation_description: str, success: bool):
        self.operation_time = operation_time
        self.operation_description = operation_description
        self.success = success

    def __str__(self):
        return f"{self.operation_time.strftime('%Y-%m-%d %H:%M:%S')}: {'✅' if self.success else '❌'} : {self.operation_description}"


def log_operation(value: DatabaseOperation):
    """ Logs an operation into the 'log' variable of the session state in streamlit"""
    st.session_state.log += [value]