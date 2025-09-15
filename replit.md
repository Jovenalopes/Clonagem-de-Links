# Overview

Link Cloner is a URL shortening and redirection service built with Flask and SQLite. The application allows users to create shortened URLs that redirect to target destinations, with optional features like UTM parameter addition, alternative domain usage, and tracking capabilities. The system uses HTTP 302 redirects to avoid X-Frame-Options blocking issues that occur with iframe-based masking approaches.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Framework
- **Flask**: Lightweight Python web framework chosen for its simplicity and rapid development capabilities
- **SQLite Database**: File-based database for storing link mappings, tracking data, and configuration options
- **Database Schema**: Single `links` table storing shortened IDs, target URLs, tracking IDs, domain preferences, UTM settings, and creation timestamps

## URL Generation and Storage
- **Short ID Generation**: Random 8-character strings using lowercase letters and digits for collision-resistant URL shortening
- **Link Storage**: Database persistence with support for link replacement and configuration updates
- **Link Retrieval**: Direct database lookup for fast redirection resolution

## Redirection Strategy
- **HTTP 302 Redirects**: Server-side redirects chosen over iframe embedding to avoid X-Frame-Options blocking
- **UTM Parameter Support**: Optional automatic addition of UTM tracking parameters to target URLs
- **Alternative Domain Configuration**: Environment-based configuration for using custom domains

## Configuration Management
- **Environment Variables**: ALT_DOMAIN configuration through environment variables
- **Boolean Flags**: Database-stored preferences for UTM addition, alternative domain usage, and masking options
- **Runtime Configuration**: Dynamic feature enabling based on environment setup

## Data Persistence
- **SQLite Integration**: Local file-based database with automatic table creation
- **Connection Management**: Per-request database connections with proper resource cleanup
- **Schema Evolution**: Support for table creation and potential future migrations

# External Dependencies

## Python Packages
- **Flask 2.2.5**: Web framework for HTTP request handling and response generation
- **SQLite3**: Built-in Python library for database operations (no external database server required)
- **urllib.parse**: Standard library for URL manipulation and parameter handling
- **os, string, random**: Standard Python libraries for file operations, string generation, and randomization

## Infrastructure Requirements
- **Python Runtime**: Python 3.x environment for application execution
- **File System Access**: Local storage for SQLite database file persistence
- **HTTP Server Capability**: Web server environment for handling HTTP requests and redirects

## Optional External Services
- **Alternative Domain**: Configurable external domain for shortened URL generation
- **UTM Tracking**: Integration capability with analytics platforms through UTM parameter injection