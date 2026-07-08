#!/usr/bin/env python3
"""
Tests for the source-control governance audit script.

This test suite verifies that the audit script correctly identifies
production services that lack GitHub governance.

Run with: python tests/test_audit_source_governance.py
Or with pytest: pytest tests/test_audit_source_governance.py -v
"""

import subprocess
import tempfile
import os
import unittest
from pathlib import Path


class TestAuditSourceGovernance(unittest.TestCase):
    """Test suite for the audit-source-governance.sh script."""

    def setUp(self):
        """Set up test fixtures."""
        self.script_path = Path(__file__).parent.parent / "scripts" / "audit-source-governance.sh"
        self.manifest_path = Path(__file__).parent.parent / "source-control-manifest.yaml"
        self.maxDiff = None

    def test_manifest_exists(self):
        """Test that the source-control manifest exists."""
        self.assertTrue(
            self.manifest_path.exists(),
            f"Manifest not found at {self.manifest_path}"
        )

    def test_script_exists(self):
        """Test that the audit script exists."""
        self.assertTrue(
            self.script_path.exists(),
            f"Audit script not found at {self.script_path}"
        )

    def test_script_is_executable(self):
        """Test that the audit script is executable."""
        is_executable = os.access(self.script_path, os.X_OK)
        self.assertTrue(
            is_executable,
            f"Audit script is not executable: {self.script_path}"
        )

    def test_audit_fails_with_ungoverned_production_services(self):
        """Test that the audit fails when production services lack GitHub governance."""
        # The current manifest has 6 ungoverned production services
        result = subprocess.run(
            [str(self.script_path), "--manifest", str(self.manifest_path)],
            capture_output=True,
            text=True
        )
        
        # The audit should fail (exit code 1) due to ungoverned production services
        self.assertEqual(
            result.returncode, 1,
            f"Expected audit to fail with exit code 1, got {result.returncode}. "
            f"Output: {result.stdout}\nError: {result.stderr}"
        )
        
        # Check that the output mentions the expected ungoverned services
        output = result.stdout + result.stderr
        expected_services = [
            "newfire-backend",
            "newfire-app",
            "newfire-nss-control",
            "newfire-nss-runner",
            "newfire-nss-portal",
            "newfire-nss-router"
        ]
        
        for service in expected_services:
            self.assertIn(
                service, output,
                f"Expected {service} to be mentioned in audit output"
            )

    def test_audit_verbose_mode(self):
        """Test that verbose mode shows additional output."""
        result = subprocess.run(
            [str(self.script_path), "--verbose", "--manifest", str(self.manifest_path)],
            capture_output=True,
            text=True
        )
        
        # Should still fail but with more output
        self.assertEqual(result.returncode, 1)
        
        # Verbose mode should show PASS entries
        self.assertIn("newfire-infra", result.stdout)
        self.assertIn("[PASS]", result.stdout)

    def test_audit_with_compliant_manifest(self):
        """Test that the audit passes when all production services are governed."""
        compliant_manifest = """
services:
  - service: test-service
    local_path: /tmp/test
    repo_url: https://github.com/test/test
    owner: test
    deployment_host: localhost
    deployment_path: /tmp/test
    container: test
    risk_level: production
    github_governed: true
    notes: Test service
"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            f.write(compliant_manifest)
            temp_manifest = f.name

        try:
            result = subprocess.run(
                [str(self.script_path), "--manifest", temp_manifest],
                capture_output=True,
                text=True
            )
            
            # The audit should pass (exit code 0) for compliant manifest
            self.assertEqual(
                result.returncode, 0,
                f"Expected audit to pass with exit code 0, got {result.returncode}. "
                f"Output: {result.stdout}\nError: {result.stderr}"
            )
            self.assertIn("AUDIT PASSED", result.stdout)
        finally:
            os.unlink(temp_manifest)

    def test_audit_with_missing_manifest(self):
        """Test that the audit fails gracefully when manifest is missing."""
        result = subprocess.run(
            [str(self.script_path), "--manifest", "/nonexistent/manifest.yaml"],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stdout + result.stderr)

    def test_audit_with_development_only_manifest(self):
        """Test that the audit passes for manifest with only development services."""
        dev_only_manifest = """
services:
  - service: dev-service
    local_path: /tmp/test
    repo_url: null
    owner: null
    deployment_host: null
    deployment_path: not deployed
    container: null
    risk_level: development
    github_governed: false
    notes: Development only
"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            f.write(dev_only_manifest)
            temp_manifest = f.name

        try:
            result = subprocess.run(
                [str(self.script_path), "--manifest", temp_manifest],
                capture_output=True,
                text=True
            )
            
            # Should pass since no production services
            self.assertEqual(result.returncode, 0)
            self.assertIn("AUDIT PASSED", result.stdout)
        finally:
            os.unlink(temp_manifest)

    def test_audit_summary_contains_correct_counts(self):
        """Test that the audit summary shows correct service counts."""
        result = subprocess.run(
            [str(self.script_path), "--manifest", str(self.manifest_path)],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 1)  # Should fail
        
        # Check for summary section
        self.assertIn("Total services in manifest:", result.stdout)
        self.assertIn("Production services:", result.stdout)
        self.assertIn("NOT governed:", result.stdout)

    def test_help_flag(self):
        """Test that --help flag shows usage information."""
        result = subprocess.run(
            [str(self.script_path), "--help"],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--verbose", result.stdout)
        self.assertIn("--manifest", result.stdout)


class TestManifestContent(unittest.TestCase):
    """Test suite to verify manifest content."""

    def test_manifest_has_all_services(self):
        """Test that the manifest contains all expected services."""
        manifest_path = Path(__file__).parent.parent / "source-control-manifest.yaml"
        
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        expected_services = [
            "newfire-backend",
            "newfire-app",
            "newfire-nss-control",
            "newfire-nss-runner",
            "newfire-nss-portal",
            "newfire-nss-router",
            "newfire-mcp",
            "newfire-sdk",
            "newfire-infra"
        ]
        
        for service in expected_services:
            self.assertIn(
                f"- service: {service}", content,
                f"Service {service} not found in manifest"
            )

    def test_manifest_has_required_fields(self):
        """Test that each service has required fields."""
        manifest_path = Path(__file__).parent.parent / "source-control-manifest.yaml"
        
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        required_fields = [
            "service:",
            "local_path:",
            "repo_url:",
            "owner:",
            "risk_level:",
            "github_governed:"
        ]
        
        for field in required_fields:
            self.assertIn(field, content, f"Required field {field} not found in manifest")

    def test_infra_repo_is_governed(self):
        """Test that the newfire-infra repo is marked as GitHub governed."""
        manifest_path = Path(__file__).parent.parent / "source-control-manifest.yaml"
        
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        # Find the newfire-infra section and verify it's marked as governed
        lines = content.split('\n')
        in_infra_section = False
        infra_has_governed_true = False
        
        for line in lines:
            if "service: newfire-infra" in line:
                in_infra_section = True
            elif in_infra_section and "- service:" in line:
                # Next service started
                break
            elif in_infra_section and "github_governed: true" in line:
                infra_has_governed_true = True
        
        self.assertTrue(
            infra_has_governed_true,
            "newfire-infra should be marked as github_governed: true"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
