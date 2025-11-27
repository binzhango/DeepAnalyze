# Design Document: Azure Blob Storage and PostgreSQL Data Sources

## Overview

This document outlines the technical design for extending DeepAnalyze with Azure Blob Storage and PostgreSQL data source capabilities. The design follows a plugin-based architecture that allows seamless integration with the existing API while maintaining security, performance, and extensibility.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Application                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              DeepAnalyze API Server                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Source Management Layer                        │  │
│  │  - DataSourceRegistry                                │  │
│  │  - ConnectionPool                                    │  │
│  │  - CredentialManager                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Source Connectors                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │   Azure    │  │ PostgreSQL │  │   Local    │    │  │
│  │  │    Blob    │  │            │  │   Files    │    │  │
│  │  └────────────┘  └────────────┘  └────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Existing API Layer                                  │  │
│  │  - Chat API                                          │  │
│  │  - File API                                          │  │
│  │  - Storage                                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              External Data Sources                          │
│  ┌────────────┐  ┌────────────┐                            │
│  │   Azure    │  │ PostgreSQL │                            │
│  │   Blob     │  │  Database  │                            │
│  │  Storage   │  │            │                            │
│  └────────────┘  └────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Data Source Abstraction Layer

#### 1.1 Base Connector Interface

**File:** `API/datasources/base.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class DataSourceType(Enum):
    AZURE_BLOB = "azure_blob"
    POSTGRESQL = "postgresql"
    LOCAL_FILE = "local_file"

@dataclass
class DataSourceConfig:
    id: str
    type: DataSourceType
    name: str
    config: Dict[str, Any]
    created_at: int
    metadata: Dict[str, Any]

@dataclass
class DataItem:
    name: str
    path: str
    size: int
    modified_at: int
    metadata: Dict[str, Any]

class DataSourceConnector(ABC):
    """Base class for all data source connectors"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._connection = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to data source"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is valid"""
        pass
    
    @abstractmethod
    async def list_items(self, path: Optional[str] = None) -> List[DataItem]:
        """List available items in data source"""
        pass
    
    @abstractmethod
    async def fetch_data(
        self, 
        identifier: str, 
        workspace: str
    ) -> str:
        """Fetch data and save to workspace, return local path"""
        pass
    
    @abstractmethod
    async def get_metadata(self, identifier: str) -> Dict[str, Any]:
        """Get metadata for specific item"""
        pass
```
