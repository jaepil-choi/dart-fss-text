"""
Configuration management using Pydantic Settings.

Automatically loads configuration from config/types.yaml and environment variables.
Provides type-safe access to:
- DART API specifications (report types, corp classes, etc.)
- MongoDB connection settings
- DART API key
"""

from pathlib import Path
from typing import Dict, Optional
import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReportTypesConfig(BaseSettings):
    """
    Configuration automatically loaded from config/types.yaml.
    
    Pydantic Settings handles file resolution and parsing automatically.
    This class provides type-safe access to DART API specifications including:
    - Report type codes (pblntf_detail_ty)
    - Corporation classifications (corp_cls)
    - Remark codes (rm)
    
    Attributes:
        pblntf_detail_ty: Dictionary of report type codes to Korean descriptions
        corp_cls: Dictionary of corporation classification codes
        rm: Dictionary of remark codes
    
    Example:
        >>> config = ReportTypesConfig()
        >>> config.is_valid_report_type('A001')
        True
        >>> config.get_report_description('A001')
        '사업보고서'
    """
    
    pblntf_detail_ty: Dict[str, str] = Field(
        default_factory=dict,
        description="Valid report type codes with Korean descriptions"
    )
    corp_cls: Dict[str, str] = Field(
        default_factory=dict,
        description="Corporation classification codes (KOSPI, KOSDAQ, etc.)"
    )
    rm: Dict[str, str] = Field(
        default_factory=dict,
        description="Remark codes for filing metadata"
    )
    
    model_config = SettingsConfigDict(
        extra='ignore'
    )
    
    @model_validator(mode='before')
    @classmethod
    def load_yaml_config(cls, data: dict) -> dict:
        """
        Load configuration from config/types.yaml if not already provided.
        
        This validator runs before field validation and loads the YAML file
        if the data dict is empty (i.e., no values were provided).
        """
        # If data already has values (e.g., from tests), don't override
        if data:
            return data
        
        # Find the config file relative to project root
        # Search upward from this file's location
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # src/dart_fss_text/config.py -> root
        config_path = project_root / 'config' / 'types.yaml'
        
        if not config_path.exists():
            # Try alternative: relative to current working directory
            config_path = Path('config/types.yaml')
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found at {config_path}. "
                f"Ensure config/types.yaml exists in project root."
            )
        
        # Load YAML
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        # Extract only the fields we need (ignore pblntf_ty which is not needed)
        return {
            'pblntf_detail_ty': yaml_data.get('pblntf_detail_ty', {}),
            'corp_cls': yaml_data.get('corp_cls', {}),
            'rm': yaml_data.get('rm', {})
        }
    
    def is_valid_report_type(self, code: Optional[str]) -> bool:
        """
        Check if a report type code is valid.
        
        Args:
            code: Report type code to validate (e.g., 'A001')
        
        Returns:
            True if code is valid, False otherwise
        
        Example:
            >>> config = ReportTypesConfig()
            >>> config.is_valid_report_type('A001')
            True
            >>> config.is_valid_report_type('INVALID')
            False
        """
        if code is None:
            return False
        return code in self.pblntf_detail_ty
    
    def get_report_description(self, code: str) -> str:
        """
        Get Korean description for a report type code.
        
        Args:
            code: Report type code (e.g., 'A001')
        
        Returns:
            Korean description string
        
        Raises:
            KeyError: If code is not found in configuration
        
        Example:
            >>> config = ReportTypesConfig()
            >>> config.get_report_description('A001')
            '사업보고서'
        """
        if code not in self.pblntf_detail_ty:
            raise KeyError(f"Unknown report type: {code}")
        return self.pblntf_detail_ty[code]


# Singleton pattern - loaded once, cached forever
_config: Optional[ReportTypesConfig] = None


def get_config() -> ReportTypesConfig:
    """
    Get global config instance (lazy-loaded singleton).
    
    The configuration is loaded once on first access and cached for
    subsequent calls. This ensures efficient memory usage and prevents
    redundant YAML parsing.
    
    Returns:
        Singleton ReportTypesConfig instance
    
    Example:
        >>> config = get_config()
        >>> config.is_valid_report_type('A001')
        True
        >>> config2 = get_config()
        >>> config is config2  # Same instance
        True
    """
    global _config
    if _config is None:
        _config = ReportTypesConfig()
    return _config


class AppConfig(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    Provides centralized access to runtime configuration:
    - MongoDB connection settings
    - DART API key
    - Other application settings
    
    Environment Variables (from .env):
        MONGO_HOST: MongoDB host (e.g., "localhost:27017")
        DB_NAME: MongoDB database name (e.g., "FS")
        COLLECTION_NAME: MongoDB collection name (e.g., "A001")
        OPENDART_API_KEY: OpenDART API key for DART API access
    
    Attributes:
        mongo_host: MongoDB host address
        db_name: MongoDB database name
        collection_name: MongoDB collection name
        opendart_api_key: OpenDART API key for DART API access
    
    Properties:
        mongodb_uri: Computed MongoDB connection URI (mongodb://{mongo_host}/)
        mongodb_database: Alias for db_name
        mongodb_collection: Alias for collection_name
    
    Example:
        >>> config = get_app_config()
        >>> config.db_name
        'FS'
        >>> config.collection_name
        'A001'
        >>> config.mongodb_uri
        'mongodb://localhost:27017/'
    """
    
    mongo_host: str = Field(
        default="localhost:27017",
        description="MongoDB host address"
    )
    
    db_name: str = Field(
        default="FS",
        description="MongoDB database name"
    )
    
    collection_name: str = Field(
        default="A001",
        description="MongoDB collection name for A001 (Annual Report) documents"
    )
    
    opendart_api_key: Optional[str] = Field(
        default=None,
        description="OpenDART API key for accessing DART API"
    )
    
    corp_list_db_dir: str = Field(
        default="data/temp",
        description="Directory path for storing corp_list CSV files"
    )
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    @property
    def mongodb_uri(self) -> str:
        """Construct MongoDB URI from host."""
        return f"mongodb://{self.mongo_host}/"
    
    @property
    def mongodb_database(self) -> str:
        """Alias for db_name for backward compatibility."""
        return self.db_name
    
    @property
    def mongodb_collection(self) -> str:
        """Alias for collection_name for backward compatibility."""
        return self.collection_name


# Singleton pattern - loaded once, cached forever
_app_config: Optional[AppConfig] = None


def get_app_config() -> AppConfig:
    """
    Get global application config instance (lazy-loaded singleton).
    
    Configuration is loaded from environment variables and .env file.
    Cached after first access for efficiency.
    
    Returns:
        Singleton AppConfig instance
    
    Example:
        >>> config = get_app_config()
        >>> config.mongodb_database
        'FS'
        >>> config2 = get_app_config()
        >>> config is config2  # Same instance
        True
    """
    global _app_config
    if _app_config is None:
        _app_config = AppConfig()
    return _app_config


# TOC (Table of Contents) Configuration
_toc_mapping: Optional[Dict[str, str]] = None


def get_toc_mapping(report_type: str = 'A001') -> Dict[str, str]:
    """
    Get TOC (Table of Contents) mapping for a report type.
    
    Loads from config/toc.yaml and caches the result. The TOC mapping
    provides a title → section_code dictionary for standardized section
    identification in DART XML files.
    
    Args:
        report_type: Report type code (e.g., 'A001' for Annual Report)
    
    Returns:
        Dictionary mapping section titles to section codes
        Example: {'I. 회사의 개요': '010000', '1. 회사의 개요': '010100', ...}
    
    Raises:
        FileNotFoundError: If config/toc.yaml not found
        KeyError: If report_type not found in TOC configuration
    
    Example:
        >>> toc = get_toc_mapping('A001')
        >>> toc['I. 회사의 개요']
        '010000'
        >>> toc2 = get_toc_mapping('A001')
        >>> toc is toc2  # Same cached instance
        True
    
    Notes:
        - Currently only supports A001 (Annual Report)
        - Result is cached after first load for efficiency
        - Mapping is flattened from hierarchical TOC structure
    """
    global _toc_mapping
    
    # Return cached result if available
    if _toc_mapping is not None:
        return _toc_mapping
    
    # Find config/toc.yaml file
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    toc_path = project_root / 'config' / 'toc.yaml'
    
    if not toc_path.exists():
        # Try alternative: relative to current working directory
        toc_path = Path('config/toc.yaml')
    
    if not toc_path.exists():
        raise FileNotFoundError(
            f"TOC config file not found at {toc_path}. "
            f"Ensure config/toc.yaml exists in project root."
        )
    
    # Load YAML
    with open(toc_path, 'r', encoding='utf-8') as f:
        toc_data = yaml.safe_load(f)
    
    if report_type not in toc_data:
        raise KeyError(
            f"Report type '{report_type}' not found in TOC configuration. "
            f"Available types: {list(toc_data.keys())}"
        )
    
    # Flatten hierarchical structure to title → code mapping
    mapping = {}
    
    def traverse(sections: list) -> None:
        """Recursively traverse TOC structure."""
        for section in sections:
            code = section['section_code']
            name = section['section_name']
            mapping[name] = code
            
            if section.get('children'):
                traverse(section['children'])
    
    traverse(toc_data[report_type])
    
    # Cache the result
    _toc_mapping = mapping
    
    return mapping

