# Custom runtime hook to fix setuptools file access issues
import sys
import os

def fix_pkg_resources():
    """Fix pkg_resources to prevent file access errors"""
    try:
        import pkg_resources
        
        # Monkey patch the problematic methods
        original_get_distribution = pkg_resources.get_distribution
        original_working_set = pkg_resources.working_set
        
        def safe_get_distribution(name):
            try:
                return original_get_distribution(name)
            except (FileNotFoundError, OSError, ImportError):
                # Return a dummy distribution
                class DummyDistribution:
                    def __init__(self, name):
                        self.project_name = name
                        self.version = "0.0.0"
                        self.location = ""
                    def __getattr__(self, name):
                        return None
                return DummyDistribution(name)
        
        # Apply the patch
        pkg_resources.get_distribution = safe_get_distribution
        
        print("🔧 Applied pkg_resources fix")
        
    except Exception as e:
        print(f"⚠️ Could not apply pkg_resources fix: {e}")

def fix_setuptools_vendor():
    """Fix setuptools vendor file access"""
    try:
        import setuptools
        import sys
        
        # Add a dummy module to sys.modules to prevent import errors
        import types
        class DummyModule(types.ModuleType):
            def __init__(self, name):
                super().__init__(name)
            def __getattr__(self, name):
                return None
        
        # Create dummy modules for problematic imports
        sys.modules['setuptools._vendor.jaraco.text'] = DummyModule('setuptools._vendor.jaraco.text')
        sys.modules['setuptools._vendor.jaraco.functools'] = DummyModule('setuptools._vendor.jaraco.functools')
        sys.modules['setuptools._vendor.jaraco.context'] = DummyModule('setuptools._vendor.jaraco.context')
        
        print("🔧 Applied setuptools vendor fix")
        
    except Exception as e:
        print(f"⚠️ Could not apply setuptools vendor fix: {e}")

# Apply fixes when this module is imported
fix_pkg_resources()
fix_setuptools_vendor() 