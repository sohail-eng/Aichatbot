#!/usr/bin/env python3
"""
Test BGP Data Analysis

This script tests the BGP-specific analysis functionality
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append('/home/azeem/Documents/upwork-projects/chat_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')
django.setup()

from ai_services.file_analyzer import FileAnalyzer

def test_bgp_analysis():
    """Test BGP data analysis functionality"""
    print("🧪 Testing BGP Data Analysis")
    print("=" * 50)
    
    # BGP data file path
    bgp_file = "/home/azeem/Documents/upwork-projects/chat_project/media/uploads/de83e3ba-31e9-42b7-8104-a74b05bdfc63_20250819_015640_BGPData.csv"
    
    if not os.path.exists(bgp_file):
        print(f"❌ BGP file not found: {bgp_file}")
        return
    
    print(f"📁 Using BGP file: {os.path.basename(bgp_file)}")
    
    try:
        # Create file analyzer
        analyzer = FileAnalyzer()
        
        # Test BGP-specific question
        test_question = "which devices has bgp state down and what's their neighbor ip"
        print(f"\n📝 Testing question: '{test_question}'")
        
        # Extract keywords
        search_keywords = analyzer._extract_search_keywords(test_question)
        print(f"✅ Keywords extracted: {', '.join(search_keywords)}")
        
        # Analyze BGP data directly
        print("\n🔍 Analyzing BGP data...")
        csv_analysis = analyzer._analyze_csv_file(bgp_file, search_keywords, test_question)
        
        if csv_analysis['relevance_score'] > 0:
            print("✅ BGP analysis successful!")
            print(f"   • Relevance score: {csv_analysis['relevance_score']}")
            print(f"   • Analysis: {csv_analysis['analysis_summary']}")
            
            # Check for BGP-specific analysis
            if 'bgp_analysis' in csv_analysis['found_data'] and csv_analysis['found_data']['bgp_analysis']:
                bgp = csv_analysis['found_data']['bgp_analysis']
                print(f"\n📊 BGP Analysis Results:")
                print(f"   • Type: {bgp.get('type')}")
                print(f"   • Summary: {bgp.get('summary')}")
                
                if 'details' in bgp:
                    details = bgp['details']
                    if 'down_states' in details:
                        print(f"   • Down BGP sessions: {details['down_states']['count']}")
                    if 'down_neighbors' in details:
                        print(f"   • Down neighbor IPs: {', '.join(details['down_neighbors'][:5])}")
                    if 'down_devices' in details:
                        print(f"   • Down devices: {', '.join(details['down_devices'][:5])}")
            else:
                print("⚠️ No BGP-specific analysis found")
        else:
            print("⚠️ No relevant data found in BGP file")
        
        # Test with mock file info
        print("\n🔍 Testing with mock file info...")
        mock_attached_files = [{
            'id': 'test_id',
            'name': os.path.basename(bgp_file),
            'type': 'csv'
        }]
        
        # Test the full analysis
        full_analysis = analyzer.analyze_question_with_files(test_question, mock_attached_files)
        
        if full_analysis['success']:
            print("✅ Full analysis successful!")
            print(f"   • Files analyzed: {full_analysis['files_analyzed']}")
            print(f"   • Data found: {'Yes' if full_analysis['found_data'] else 'No'}")
            
            if full_analysis['found_data']:
                print(f"   • Found data instances: {len(full_analysis['found_data'])}")
            
            print(f"\n📊 Comprehensive Analysis:")
            print(full_analysis['comprehensive_analysis'])
        else:
            print(f"❌ Full analysis failed: {full_analysis.get('error')}")
        
        print("\n🎉 BGP Analysis Test Completed!")
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bgp_analysis()
