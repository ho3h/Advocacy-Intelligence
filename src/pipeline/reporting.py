"""Reporting and logging for pipeline runs."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class PipelineReporter:
    """Handles logging, reporting, and cost tracking for pipeline runs."""
    
    def __init__(self):
        """Initialize reporter."""
        self.logs_dir = Path('logs')
        self.logs_dir.mkdir(exist_ok=True)
        
        self.start_time = datetime.now()
        self.logs = []
        self.errors = []
        self.stats = {
            'vendors_processed': 0,
            'phases_completed': {},
            'urls_discovered': 0,
            'urls_scraped': 0,
            'references_loaded': 0,
            'references_classified': 0,
            'costs': {
                'hyperbrowser': 0,
                'gemini': 0
            }
        }
    
    def log(self, message: str):
        """Log a message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        print(log_entry)
    
    def log_error(self, error: str):
        """Log an error."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        error_entry = f"[{timestamp}] ERROR: {error}"
        self.errors.append(error_entry)
        self.logs.append(error_entry)
        print(f"❌ {error_entry}")
    
    def update_stats(self, phase: int, stats: Dict):
        """Update statistics for a phase."""
        phase_key = f'phase{phase}'
        if phase_key not in self.stats['phases_completed']:
            self.stats['phases_completed'][phase_key] = 0
        self.stats['phases_completed'][phase_key] += 1
        
        # Update phase-specific stats
        if phase == 1:
            self.stats['urls_discovered'] += stats.get('new', 0)
        elif phase == 2:
            self.stats['urls_scraped'] += stats.get('scraped', 0)
        elif phase == 3:
            self.stats['references_loaded'] += stats.get('loaded', 0)
        elif phase == 4:
            self.stats['references_classified'] += stats.get('classified', 0)
    
    def estimate_costs(self, urls_scraped: int, references_classified: int) -> Dict:
        """
        Estimate costs for pipeline run.
        
        Args:
            urls_scraped: Number of URLs scraped (HyperBrowser.ai)
            references_classified: Number of references classified (Gemini)
            
        Returns:
            Dict with cost estimates
        """
        # HyperBrowser.ai: ~$0.01-0.05 per page
        hyperbrowser_cost = urls_scraped * 0.03  # Average
        
        # Gemini Flash: ~$0.001-0.01 per classification
        gemini_cost = references_classified * 0.005  # Average
        
        return {
            'hyperbrowser': hyperbrowser_cost,
            'gemini': gemini_cost,
            'total': hyperbrowser_cost + gemini_cost
        }
    
    def generate_summary(self, results: Dict) -> Dict:
        """
        Generate summary report from pipeline results.
        
        Args:
            results: Results dict from run_all_vendors
            
        Returns:
            Summary dict
        """
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate totals
        total_discovered = 0
        total_scraped = 0
        total_loaded = 0
        total_classified = 0
        
        for vendor_key, vendor_results in results.items():
            if 'error' in vendor_results:
                continue
            
            for phase_key, phase_results in vendor_results.items():
                if 'error' in phase_results:
                    continue
                
                if phase_key == 'phase1':
                    total_discovered += phase_results.get('new', 0)
                elif phase_key == 'phase2':
                    total_scraped += phase_results.get('scraped', 0)
                elif phase_key == 'phase3':
                    total_loaded += phase_results.get('loaded', 0)
                elif phase_key == 'phase4':
                    total_classified += phase_results.get('classified', 0)
        
        # Estimate costs
        costs = self.estimate_costs(total_scraped, total_classified)
        
        summary = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'elapsed_seconds': elapsed_time,
            'vendors_processed': len(results),
            'totals': {
                'urls_discovered': total_discovered,
                'urls_scraped': total_scraped,
                'references_loaded': total_loaded,
                'references_classified': total_classified,
            },
            'costs': costs,
            'errors': len(self.errors),
            'results': results
        }
        
        return summary
    
    def save_report(self, summary: Dict):
        """
        Save summary report to JSON file.
        
        Args:
            summary: Summary dict from generate_summary
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_file = self.logs_dir / f'pipeline_report_{timestamp}.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.log(f"Report saved to: {report_file}")
    
    def save_error_log(self):
        """Save error log to file."""
        if not self.errors:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        error_file = self.logs_dir / f'pipeline_errors_{timestamp}.log'
        
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.errors))
        
        self.log(f"Error log saved to: {error_file}")
    
    def print_summary_table(self, summary: Dict):
        """Print a formatted summary table."""
        print("\n" + "="*70)
        print("PIPELINE SUMMARY")
        print("="*70)
        
        print(f"\nVendors Processed: {summary['vendors_processed']}")
        print(f"Elapsed Time: {summary['elapsed_seconds']:.1f} seconds ({summary['elapsed_seconds']/60:.1f} minutes)")
        
        print("\nTotals:")
        totals = summary['totals']
        print(f"  URLs Discovered: {totals['urls_discovered']}")
        print(f"  URLs Scraped: {totals['urls_scraped']}")
        print(f"  References Loaded: {totals['references_loaded']}")
        print(f"  References Classified: {totals['references_classified']}")
        
        print("\nEstimated Costs:")
        costs = summary['costs']
        print(f"  HyperBrowser.ai: ${costs['hyperbrowser']:.2f}")
        print(f"  Gemini API: ${costs['gemini']:.2f}")
        print(f"  Total: ${costs['total']:.2f}")
        
        if summary['errors'] > 0:
            print(f"\n⚠ Errors: {summary['errors']} (check error log)")
        
        print("="*70 + "\n")

