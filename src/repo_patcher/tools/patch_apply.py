"""Safe patch application tool with backup and rollback capabilities."""
import os
import shutil
import difflib
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class PatchOperation:
    """Represents a single patch operation."""
    operation_type: str  # "replace", "insert", "delete", "create", "remove"
    file_path: str
    line_number: Optional[int] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    backup_path: Optional[str] = None


@dataclass
class PatchResult:
    """Result of applying a patch."""
    success: bool
    file_path: str
    operation: str
    lines_changed: int
    backup_created: bool
    backup_path: Optional[str] = None
    error: Optional[str] = None


class PatchApplyTool(BaseTool):
    """Tool for safely applying code patches with backup and rollback."""
    
    def __init__(self):
        super().__init__("patch_apply")
        self.backup_dir_name = '.repo_patcher_backups'
        self.max_backup_age_days = 7  # Clean up old backups
        
    async def _execute(self, **kwargs) -> Any:
        """Execute patch application operation."""
        operation = kwargs.get('operation', 'apply_patches')
        repo_path = Path(kwargs.get('repo_path', '.'))
        
        if operation == 'apply_patches':
            result = await self._apply_patches(repo_path, kwargs)
        elif operation == 'create_backup':
            result = await self._create_backup(repo_path, kwargs)
        elif operation == 'restore_backup':
            result = await self._restore_backup(repo_path, kwargs)
        elif operation == 'rollback_changes':
            result = await self._rollback_changes(repo_path, kwargs)
        elif operation == 'validate_patches':
            result = await self._validate_patches(kwargs.get('patches', []))
        elif operation == 'preview_changes':
            result = await self._preview_changes(repo_path, kwargs)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        if not result.success:
            raise RuntimeError(result.error or "Operation failed")
        
        return result.data
    
    async def _apply_patches(self, repo_path: Path, params: Dict[str, Any]) -> ToolResult:
        """Apply a list of patches safely with backups."""
        patches = params.get('patches', [])
        create_backups = params.get('create_backups', True)
        validate_before = params.get('validate_before', True)
        dry_run = params.get('dry_run', False)
        
        if not patches:
            return ToolResult(
                success=False,
                data={},
                error="No patches provided",
                cost=0.0
            )
        
        # Validate patches first if requested
        if validate_before:
            validation_result = await self._validate_patches(patches)
            if not validation_result.success:
                return validation_result
        
        results = []
        backup_dir = None
        
        try:
            # Create backup directory if needed
            if create_backups and not dry_run:
                backup_dir = await self._create_backup_directory(repo_path)
            
            # Apply each patch
            for i, patch_data in enumerate(patches):
                if dry_run:
                    # For dry run, just validate the patch can be applied
                    result = await self._simulate_patch_application(repo_path, patch_data)
                else:
                    result = await self._apply_single_patch(
                        repo_path, patch_data, backup_dir, i
                    )
                results.append(result)
                
                # Stop on first failure if not in dry run mode
                if not result.success and not dry_run:
                    logger.error(f"Patch application failed, stopping at patch {i}")
                    break
            
            # Calculate summary statistics
            successful_patches = sum(1 for r in results if r.success)
            total_lines_changed = sum(r.lines_changed for r in results if r.success)
            
            return ToolResult(
                success=all(r.success for r in results),
                data={
                    'patch_results': [self._patch_result_to_dict(r) for r in results],
                    'summary': {
                        'total_patches': len(patches),
                        'successful_patches': successful_patches,
                        'failed_patches': len(patches) - successful_patches,
                        'total_lines_changed': total_lines_changed,
                        'backup_directory': str(backup_dir) if backup_dir else None,
                        'dry_run': dry_run
                    }
                },
                error=None if all(r.success for r in results) else "Some patches failed",
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Patch application failed: {e}")
            return ToolResult(
                success=False,
                data={'partial_results': [self._patch_result_to_dict(r) for r in results]},
                error=str(e),
                cost=0.0
            )
    
    async def _apply_single_patch(self, repo_path: Path, patch_data: Dict[str, Any], 
                                 backup_dir: Optional[Path], patch_index: int) -> PatchResult:
        """Apply a single patch to a file."""
        file_path = repo_path / patch_data.get('file_path', '')
        modifications = patch_data.get('modifications', [])
        
        if not file_path.exists() and not any(mod.get('operation') == 'create' for mod in modifications):
            return PatchResult(
                success=False,
                file_path=str(file_path),
                operation="apply",
                lines_changed=0,
                backup_created=False,
                error=f"File does not exist: {file_path}"
            )
        
        backup_path = None
        lines_changed = 0
        
        try:
            # Create backup if directory provided
            if backup_dir and file_path.exists():
                backup_path = await self._backup_file(file_path, backup_dir, patch_index)
            
            # Read original file if it exists
            original_lines = []
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_lines = f.readlines()
            
            # Apply modifications in reverse line order to maintain line numbers
            modified_lines = original_lines.copy()
            sorted_modifications = sorted(
                modifications, 
                key=lambda x: x.get('line_number', 0), 
                reverse=True
            )
            
            for mod in sorted_modifications:
                operation = mod.get('operation', 'replace')
                line_num = mod.get('line_number', 0)
                old_content = mod.get('old_content', '')
                new_content = mod.get('new_content', '')
                
                if operation == 'replace':
                    if 1 <= line_num <= len(modified_lines):
                        # Verify old content matches
                        current_line = modified_lines[line_num - 1].rstrip()
                        if old_content and current_line != old_content.rstrip():
                            logger.warning(
                                f"Content mismatch at line {line_num}. "
                                f"Expected: '{old_content.rstrip()}', "
                                f"Found: '{current_line}'"
                            )
                        
                        modified_lines[line_num - 1] = new_content + '\n' if not new_content.endswith('\n') else new_content
                        lines_changed += 1
                
                elif operation == 'insert':
                    if 0 <= line_num <= len(modified_lines):
                        modified_lines.insert(line_num, new_content + '\n' if not new_content.endswith('\n') else new_content)
                        lines_changed += 1
                
                elif operation == 'delete':
                    if 1 <= line_num <= len(modified_lines):
                        del modified_lines[line_num - 1]
                        lines_changed += 1
                
                elif operation == 'create':
                    # Create new file with content
                    modified_lines = [new_content + '\n' if not new_content.endswith('\n') else new_content]
                    lines_changed = 1
            
            # Write modified content back to file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)
            
            return PatchResult(
                success=True,
                file_path=str(file_path),
                operation="apply",
                lines_changed=lines_changed,
                backup_created=backup_path is not None,
                backup_path=str(backup_path) if backup_path else None
            )
            
        except Exception as e:
            logger.error(f"Failed to apply patch to {file_path}: {e}")
            
            # Restore from backup if we created one
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, file_path)
                    logger.info(f"Restored {file_path} from backup")
                except Exception as restore_error:
                    logger.error(f"Failed to restore from backup: {restore_error}")
            
            return PatchResult(
                success=False,
                file_path=str(file_path),
                operation="apply",
                lines_changed=0,
                backup_created=backup_path is not None,
                backup_path=str(backup_path) if backup_path else None,
                error=str(e)
            )
    
    async def _simulate_patch_application(self, repo_path: Path, patch_data: Dict[str, Any]) -> PatchResult:
        """Simulate patch application for dry run mode."""
        file_path = repo_path / patch_data.get('file_path', '')
        modifications = patch_data.get('modifications', [])
        
        if not file_path.exists():
            return PatchResult(
                success=False,
                file_path=str(file_path),
                operation="simulate",
                lines_changed=0,
                backup_created=False,
                error=f"File does not exist: {file_path}"
            )
        
        try:
            # Read file and simulate changes
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            lines_that_would_change = 0
            issues = []
            
            for mod in modifications:
                operation = mod.get('operation', 'replace')
                line_num = mod.get('line_number', 0)
                old_content = mod.get('old_content', '')
                
                if operation in ['replace', 'delete']:
                    if 1 <= line_num <= len(lines):
                        current_line = lines[line_num - 1].rstrip()
                        if old_content and current_line != old_content.rstrip():
                            issues.append(
                                f"Line {line_num} content mismatch: "
                                f"expected '{old_content.rstrip()}', found '{current_line}'"
                            )
                        else:
                            lines_that_would_change += 1
                    else:
                        issues.append(f"Line {line_num} is out of range (file has {len(lines)} lines)")
                
                elif operation == 'insert':
                    if 0 <= line_num <= len(lines):
                        lines_that_would_change += 1
                    else:
                        issues.append(f"Insert position {line_num} is out of range")
            
            return PatchResult(
                success=len(issues) == 0,
                file_path=str(file_path),
                operation="simulate",
                lines_changed=lines_that_would_change,
                backup_created=False,
                error="; ".join(issues) if issues else None
            )
            
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=str(file_path),
                operation="simulate",
                lines_changed=0,
                backup_created=False,
                error=str(e)
            )
    
    async def _create_backup_directory(self, repo_path: Path) -> Path:
        """Create backup directory with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = repo_path / self.backup_dir_name / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up old backups
        await self._cleanup_old_backups(repo_path)
        
        return backup_dir
    
    async def _backup_file(self, file_path: Path, backup_dir: Path, patch_index: int) -> Path:
        """Create backup of a single file."""
        # Preserve relative path structure in backup
        repo_root = backup_dir.parent.parent  # Go up from backup_dir to repo root
        relative_path = file_path.relative_to(repo_root)
        
        backup_path = backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
        
        return backup_path
    
    async def _cleanup_old_backups(self, repo_path: Path) -> None:
        """Clean up backup directories older than max_backup_age_days."""
        backup_root = repo_path / self.backup_dir_name
        if not backup_root.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (self.max_backup_age_days * 24 * 3600)
        
        try:
            for backup_dir in backup_root.iterdir():
                if backup_dir.is_dir() and backup_dir.stat().st_mtime < cutoff_time:
                    shutil.rmtree(backup_dir)
                    logger.debug(f"Cleaned up old backup: {backup_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up old backups: {e}")
    
    async def _validate_patches(self, patches: List[Dict[str, Any]]) -> ToolResult:
        """Validate patch structure and content."""
        issues = []
        
        for i, patch in enumerate(patches):
            patch_issues = []
            
            # Check required fields
            if 'file_path' not in patch:
                patch_issues.append("Missing 'file_path' field")
            
            if 'modifications' not in patch:
                patch_issues.append("Missing 'modifications' field")
            elif not isinstance(patch['modifications'], list):
                patch_issues.append("'modifications' must be a list")
            else:
                # Validate each modification
                for j, mod in enumerate(patch['modifications']):
                    if 'operation' not in mod:
                        patch_issues.append(f"Modification {j}: missing 'operation' field")
                    elif mod['operation'] not in ['replace', 'insert', 'delete', 'create']:
                        patch_issues.append(f"Modification {j}: invalid operation '{mod['operation']}'")
                    
                    if mod.get('operation') in ['replace', 'insert', 'delete'] and 'line_number' not in mod:
                        patch_issues.append(f"Modification {j}: missing 'line_number' for {mod.get('operation')} operation")
                    
                    if mod.get('operation') in ['replace', 'insert', 'create'] and 'new_content' not in mod:
                        patch_issues.append(f"Modification {j}: missing 'new_content' for {mod.get('operation')} operation")
            
            if patch_issues:
                issues.append(f"Patch {i}: {'; '.join(patch_issues)}")
        
        return ToolResult(
            success=len(issues) == 0,
            data={'validation_issues': issues},
            error=f"Validation failed: {'; '.join(issues)}" if issues else None,
            cost=0.0
        )
    
    async def _preview_changes(self, repo_path: Path, params: Dict[str, Any]) -> ToolResult:
        """Preview what changes would be made by patches."""
        patches = params.get('patches', [])
        
        previews = []
        
        try:
            for patch_data in patches:
                file_path = repo_path / patch_data.get('file_path', '')
                
                if not file_path.exists():
                    previews.append({
                        'file_path': str(file_path),
                        'status': 'file_not_found',
                        'diff': None
                    })
                    continue
                
                # Read original file
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_lines = f.readlines()
                
                # Apply modifications to create new version
                modified_lines = original_lines.copy()
                modifications = patch_data.get('modifications', [])
                
                # Sort by line number in reverse order
                sorted_mods = sorted(
                    modifications,
                    key=lambda x: x.get('line_number', 0),
                    reverse=True
                )
                
                for mod in sorted_mods:
                    operation = mod.get('operation', 'replace')
                    line_num = mod.get('line_number', 0)
                    new_content = mod.get('new_content', '')
                    
                    if operation == 'replace' and 1 <= line_num <= len(modified_lines):
                        modified_lines[line_num - 1] = new_content + '\n' if not new_content.endswith('\n') else new_content
                    elif operation == 'insert' and 0 <= line_num <= len(modified_lines):
                        modified_lines.insert(line_num, new_content + '\n' if not new_content.endswith('\n') else new_content)
                    elif operation == 'delete' and 1 <= line_num <= len(modified_lines):
                        del modified_lines[line_num - 1]
                
                # Generate diff
                diff = list(difflib.unified_diff(
                    original_lines,
                    modified_lines,
                    fromfile=f"a/{patch_data.get('file_path', '')}",
                    tofile=f"b/{patch_data.get('file_path', '')}",
                    lineterm=''
                ))
                
                previews.append({
                    'file_path': str(file_path),
                    'status': 'success',
                    'diff': ''.join(diff),
                    'lines_added': sum(1 for line in diff if line.startswith('+')),
                    'lines_removed': sum(1 for line in diff if line.startswith('-'))
                })
        
        except Exception as e:
            return ToolResult(
                success=False,
                data={'partial_previews': previews},
                error=str(e),
                cost=0.0
            )
        
        return ToolResult(
            success=True,
            data={'previews': previews},
            error=None,
            cost=0.0
        )
    
    async def _create_backup(self, repo_path: Path, params: Dict[str, Any]) -> ToolResult:
        """Create backup of specific files or entire repository."""
        files = params.get('files', [])
        backup_name = params.get('backup_name', f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        try:
            backup_dir = repo_path / self.backup_dir_name / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backed_up_files = []
            
            if not files:
                # Backup entire repository
                for root, dirs, filenames in os.walk(repo_path):
                    # Skip the backup directory itself
                    if self.backup_dir_name in str(root):
                        continue
                    
                    for filename in filenames:
                        src_path = Path(root) / filename
                        rel_path = src_path.relative_to(repo_path)
                        
                        dest_path = backup_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(src_path, dest_path)
                        backed_up_files.append(str(rel_path))
            else:
                # Backup specific files
                for file_path in files:
                    src_path = repo_path / file_path
                    if src_path.exists():
                        dest_path = backup_dir / file_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(src_path, dest_path)
                        backed_up_files.append(file_path)
            
            return ToolResult(
                success=True,
                data={
                    'backup_directory': str(backup_dir),
                    'backup_name': backup_name,
                    'files_backed_up': len(backed_up_files),
                    'backup_files': backed_up_files[:100]  # Limit for large backups
                },
                error=None,
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                cost=0.0
            )
    
    async def _restore_backup(self, repo_path: Path, params: Dict[str, Any]) -> ToolResult:
        """Restore files from a backup."""
        backup_name = params.get('backup_name', '')
        files = params.get('files', [])  # If empty, restore all files
        
        if not backup_name:
            return ToolResult(
                success=False,
                data={},
                error="Backup name is required",
                cost=0.0
            )
        
        backup_dir = repo_path / self.backup_dir_name / backup_name
        
        if not backup_dir.exists():
            return ToolResult(
                success=False,
                data={},
                error=f"Backup directory not found: {backup_dir}",
                cost=0.0
            )
        
        try:
            restored_files = []
            
            if not files:
                # Restore all files from backup
                for root, dirs, filenames in os.walk(backup_dir):
                    for filename in filenames:
                        src_path = Path(root) / filename
                        rel_path = src_path.relative_to(backup_dir)
                        
                        dest_path = repo_path / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(src_path, dest_path)
                        restored_files.append(str(rel_path))
            else:
                # Restore specific files
                for file_path in files:
                    src_path = backup_dir / file_path
                    if src_path.exists():
                        dest_path = repo_path / file_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(src_path, dest_path)
                        restored_files.append(file_path)
            
            return ToolResult(
                success=True,
                data={
                    'backup_name': backup_name,
                    'files_restored': len(restored_files),
                    'restored_files': restored_files
                },
                error=None,
                cost=0.0
            )
            
        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e),
                cost=0.0
            )
    
    async def _rollback_changes(self, repo_path: Path, params: Dict[str, Any]) -> ToolResult:
        """Rollback to the most recent backup."""
        backup_dirs = []
        backup_root = repo_path / self.backup_dir_name
        
        if backup_root.exists():
            backup_dirs = [d for d in backup_root.iterdir() if d.is_dir()]
            backup_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not backup_dirs:
            return ToolResult(
                success=False,
                data={},
                error="No backups found",
                cost=0.0
            )
        
        # Use the most recent backup
        latest_backup = backup_dirs[0]
        
        return await self._restore_backup(repo_path, {
            'backup_name': latest_backup.name,
            'files': params.get('files', [])
        })
    
    def _patch_result_to_dict(self, result: PatchResult) -> Dict[str, Any]:
        """Convert PatchResult to dictionary."""
        return {
            'success': result.success,
            'file_path': result.file_path,
            'operation': result.operation,
            'lines_changed': result.lines_changed,
            'backup_created': result.backup_created,
            'backup_path': result.backup_path,
            'error': result.error
        }
    
    def _calculate_cost(self, **kwargs) -> float:
        """Patch operations are free."""
        _ = kwargs  # Suppress unused parameter warning
        return 0.0