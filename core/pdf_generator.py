"""
PDF Report Generator for TTB COLA Market Insights
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Frame, PageTemplate
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import io
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO

class MarketInsightsPDFGenerator:
    def __init__(self):
        self.primary_color = HexColor('#2563eb')
        self.secondary_color = HexColor('#3b82f6')
        self.accent_color = HexColor('#10b981')
        self.text_color = HexColor('#1f2937')
        self.light_gray = HexColor('#f3f4f6')
        
    def generate_pdf(self, insights_data, output_buffer=None):
        """Generate a comprehensive PDF report from market insights data"""
        if output_buffer is None:
            output_buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get styles
        styles = self._get_custom_styles()
        
        # Add title page
        elements.extend(self._create_title_page(insights_data, styles))
        elements.append(PageBreak())
        
        # Executive summary
        elements.extend(self._create_executive_summary(insights_data, styles))
        elements.append(PageBreak())
        
        # Market overview
        elements.extend(self._create_market_overview(insights_data, styles))
        elements.append(PageBreak())
        
        # Geographic analysis
        elements.extend(self._create_geographic_analysis(insights_data, styles))
        elements.append(PageBreak())
        
        # Product analysis
        elements.extend(self._create_product_analysis(insights_data, styles))
        elements.append(PageBreak())
        
        # Importer analysis
        elements.extend(self._create_importer_analysis(insights_data, styles))
        elements.append(PageBreak())
        
        # Market concentration
        elements.extend(self._create_market_concentration(insights_data, styles))
        elements.append(PageBreak())
        
        # Top performers
        elements.extend(self._create_top_performers(insights_data, styles))
        
        # Build PDF
        doc.build(elements, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        # Reset buffer position
        output_buffer.seek(0)
        return output_buffer
    
    def _get_custom_styles(self):
        """Create custom paragraph styles"""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=self.primary_color,
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Heading 1
        styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=self.primary_color,
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Heading 2
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=self.secondary_color,
            spaceAfter=6,
            spaceBefore=12
        ))
        
        # Body text
        styles.add(ParagraphStyle(
            name='CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            textColor=self.text_color,
            alignment=TA_JUSTIFY
        ))
        
        # Metric style
        styles.add(ParagraphStyle(
            name='MetricValue',
            parent=styles['Normal'],
            fontSize=16,
            textColor=self.primary_color,
            alignment=TA_CENTER
        ))
        
        # Metric label
        styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=styles['Normal'],
            fontSize=10,
            textColor=self.text_color,
            alignment=TA_CENTER
        ))
        
        return styles
    
    def _create_title_page(self, data, styles):
        """Create the title page"""
        elements = []
        
        # Add spacing
        elements.append(Spacer(1, 2*inch))
        
        # Title
        title = Paragraph("TTB COLA Registry<br/>Market Insights Report", styles['CustomTitle'])
        elements.append(title)
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        date_para = Paragraph(f"Generated: {date_str}", styles['CustomBody'])
        elements.append(date_para)
        
        elements.append(Spacer(1, 1*inch))
        
        # Key metrics summary table
        overview = data.get('overview', {})
        metrics_data = [
            ['Total Brands', f"{overview.get('total_brands', 0):,}"],
            ['Total SKUs', f"{overview.get('total_skus', 0):,}"],
            ['Total Importers', f"{overview.get('total_importers', 0):,}"],
            ['Active Importers', f"{overview.get('active_importers', 0):,}"],
            ['Brands with Websites', f"{overview.get('brands_with_websites', 0):,}"],
            ['Enrichment Rate', f"{overview.get('enrichment_rate', 0)}%"]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.light_gray),
            ('TEXTCOLOR', (0, 0), (0, -1), self.text_color),
            ('TEXTCOLOR', (1, 0), (1, -1), self.primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.white)
        ]))
        
        elements.append(metrics_table)
        
        return elements
    
    def _create_executive_summary(self, data, styles):
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph("Executive Summary", styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        overview = data.get('overview', {})
        geographic = data.get('geographic_analysis', {})
        product = data.get('product_analysis', {})
        concentration = data.get('market_concentration', {})
        
        # Summary text
        summary_text = f"""
        The TTB COLA Registry currently contains <b>{overview.get('total_brands', 0):,}</b> brands with 
        <b>{overview.get('total_skus', 0):,}</b> SKUs across <b>{overview.get('total_importers', 0):,}</b> importers. 
        Of these, <b>{overview.get('active_importers', 0)}</b> importers are actively managing brands.
        
        <br/><br/>
        
        The market shows a <b>{concentration.get('market_structure', 'Unknown')}</b> structure with a 
        Herfindahl-Hirschman Index of <b>{concentration.get('herfindahl_index', 0)}</b>. 
        The top 4 importers control <b>{concentration.get('concentration_ratio_cr4', 0)}%</b> of the market.
        
        <br/><br/>
        
        Geographic diversity spans <b>{geographic.get('geographic_diversity_score', 0)}</b> countries, 
        with <b>{geographic.get('international_vs_domestic', {}).get('domestic_percentage', 0)}%</b> 
        of brands being domestic. Product diversity includes <b>{product.get('product_diversity_score', 0)}</b> 
        distinct alcohol types.
        
        <br/><br/>
        
        Current enrichment efforts have achieved a <b>{overview.get('enrichment_rate', 0)}%</b> coverage rate, 
        with <b>{overview.get('brands_with_websites', 0)}</b> brands having identified websites.
        """
        
        elements.append(Paragraph(summary_text, styles['CustomBody']))
        
        return elements
    
    def _create_market_overview(self, data, styles):
        """Create market overview section"""
        elements = []
        
        elements.append(Paragraph("Market Overview", styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        overview = data.get('overview', {})
        growth = data.get('growth_indicators', {})
        
        # Create overview metrics table
        overview_data = [
            ['Metric', 'Value', 'Industry Benchmark'],
            ['Total Brands', f"{overview.get('total_brands', 0):,}", 'N/A'],
            ['Total SKUs', f"{overview.get('total_skus', 0):,}", 'N/A'],
            ['Average SKUs per Brand', f"{overview.get('avg_skus_per_brand', 0)}", '2.5-3.5'],
            ['Active Importers', f"{overview.get('active_importers', 0)}", 'N/A'],
            ['Avg Brands per Importer', f"{growth.get('brands_per_importer', {}).get('average', 0)}", '5-10'],
            ['Website Coverage', f"{overview.get('enrichment_rate', 0)}%", '15-25%']
        ]
        
        overview_table = Table(overview_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))
        
        elements.append(overview_table)
        
        # SKU distribution
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("SKU Distribution Analysis", styles['CustomHeading2']))
        
        sku_dist = data.get('product_analysis', {}).get('sku_distribution', [])
        if sku_dist:
            sku_data = [['Range', 'Brand Count', 'Percentage']]
            total_brands = sum(item['count'] for item in sku_dist)
            
            for item in sku_dist:
                percentage = round(item['count'] / total_brands * 100, 1)
                sku_data.append([item['range'], str(item['count']), f"{percentage}%"])
            
            sku_table = Table(sku_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            sku_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(sku_table)
        
        return elements
    
    def _create_geographic_analysis(self, data, styles):
        """Create geographic analysis section"""
        elements = []
        
        elements.append(Paragraph("Geographic Analysis", styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        geographic = data.get('geographic_analysis', {})
        
        # International vs Domestic
        intl_vs_dom = geographic.get('international_vs_domestic', {})
        elements.append(Paragraph("Market Distribution", styles['CustomHeading2']))
        
        dist_text = f"""
        The market comprises <b>{intl_vs_dom.get('domestic_percentage', 0)}%</b> domestic brands 
        ({intl_vs_dom.get('domestic', 0):,} brands) and <b>{100 - intl_vs_dom.get('domestic_percentage', 0)}%</b> 
        international brands ({intl_vs_dom.get('international', 0):,} brands).
        """
        elements.append(Paragraph(dist_text, styles['CustomBody']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Top countries table
        elements.append(Paragraph("Top Producing Countries", styles['CustomHeading2']))
        
        countries = geographic.get('top_countries', [])[:10]
        if countries:
            country_data = [['Rank', 'Country', 'Brand Count', 'Market Share']]
            for idx, country in enumerate(countries, 1):
                country_data.append([
                    str(idx),
                    country['name'],
                    f"{country['count']:,}",
                    f"{country['percentage']}%"
                ])
            
            country_table = Table(country_data, colWidths=[0.7*inch, 2.5*inch, 1.2*inch, 1.2*inch])
            country_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(country_table)
        
        # Top US states
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("Top US States", styles['CustomHeading2']))
        
        states = geographic.get('top_states', [])[:10]
        if states:
            state_data = [['Rank', 'State', 'Brand Count', 'Market Share']]
            for idx, state in enumerate(states, 1):
                state_data.append([
                    str(idx),
                    state['name'],
                    f"{state['count']:,}",
                    f"{state['percentage']}%"
                ])
            
            state_table = Table(state_data, colWidths=[0.7*inch, 2.5*inch, 1.2*inch, 1.2*inch])
            state_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(state_table)
        
        return elements
    
    def _create_product_analysis(self, data, styles):
        """Create product analysis section"""
        elements = []
        
        elements.append(Paragraph("Product Analysis", styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        product = data.get('product_analysis', {})
        
        # Category distribution
        elements.append(Paragraph("Category Distribution", styles['CustomHeading2']))
        
        categories = product.get('category_distribution', {})
        if categories:
            total = sum(categories.values())
            cat_data = [['Category', 'Brand Count', 'Market Share']]
            
            for cat_name, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                percentage = round(count / total * 100, 1) if total else 0
                cat_data.append([cat_name, f"{count:,}", f"{percentage}%"])
            
            cat_table = Table(cat_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            cat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.accent_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(cat_table)
        
        # Top alcohol types
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("Top Alcohol Types", styles['CustomHeading2']))
        
        types = product.get('top_alcohol_types', [])[:15]
        if types:
            type_data = [['Rank', 'Type', 'Count', 'Share']]
            for idx, type_info in enumerate(types, 1):
                type_data.append([
                    str(idx),
                    type_info['type'][:30],  # Truncate long names
                    f"{type_info['count']:,}",
                    f"{type_info['percentage']}%"
                ])
            
            type_table = Table(type_data, colWidths=[0.5*inch, 3*inch, 1*inch, 1*inch])
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(type_table)
        
        return elements
    
    def _create_importer_analysis(self, data, styles):
        """Create importer analysis section"""
        elements = []
        
        elements.append(Paragraph("Importer Analysis", styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        importer = data.get('importer_analysis', {})
        
        # Market share distribution
        market_share = importer.get('market_share_distribution', {})
        if market_share:
            share_text = f"""
            The top 10 importers control <b>{market_share.get('top_10_percentage', 0)}%</b> of the market 
            with <b>{market_share.get('top_10_importers', 0):,}</b> brands, while the remaining importers 
            manage <b>{market_share.get('others', 0):,}</b> brands.
            """
            elements.append(Paragraph(share_text, styles['CustomBody']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Top importers table
        elements.append(Paragraph("Top Importers by Brand Count", styles['CustomHeading2']))
        
        top_importers = importer.get('top_importers', [])[:15]
        if top_importers:
            importer_data = [['Rank', 'Company', 'Brands', 'Market Share']]
            for idx, imp in enumerate(top_importers, 1):
                company_name = imp['name'][:40] if imp['name'] else 'Unknown'  # Truncate long names
                importer_data.append([
                    str(idx),
                    company_name,
                    str(imp['brand_count']),
                    f"{imp['market_share']}%"
                ])
            
            importer_table = Table(importer_data, colWidths=[0.5*inch, 3.5*inch, 0.8*inch, 1*inch])
            importer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(importer_table)
        
        # Concentration analysis
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("Importer Concentration", styles['CustomHeading2']))
        
        concentration = importer.get('concentration_analysis', [])
        if concentration:
            conc_data = [['Brand Range', 'Number of Importers']]
            for item in concentration:
                conc_data.append([item['range'], str(item['count'])])
            
            conc_table = Table(conc_data, colWidths=[2.5*inch, 2*inch])
            conc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(conc_table)
        
        return elements
    
    def _create_market_concentration(self, data, styles):
        """Create market concentration analysis section"""
        elements = []
        
        elements.append(Paragraph("Market Concentration Analysis", styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        concentration = data.get('market_concentration', {})
        
        # Market structure explanation
        structure_text = f"""
        The market exhibits a <b>{concentration.get('market_structure', 'Unknown')}</b> structure based on the 
        Herfindahl-Hirschman Index (HHI) of <b>{concentration.get('herfindahl_index', 0)}</b>.
        
        <br/><br/>
        
        <b>Concentration Ratios:</b><br/>
        • CR4 (Top 4 importers): <b>{concentration.get('concentration_ratio_cr4', 0)}%</b><br/>
        • CR8 (Top 8 importers): <b>{concentration.get('concentration_ratio_cr8', 0)}%</b>
        
        <br/><br/>
        
        <b>Market Structure Interpretation:</b><br/>
        • HHI < 1,500: Competitive market<br/>
        • HHI 1,500-2,500: Moderately concentrated<br/>
        • HHI > 2,500: Highly concentrated
        """
        
        elements.append(Paragraph(structure_text, styles['CustomBody']))
        
        # Concentration metrics table
        elements.append(Spacer(1, 0.3*inch))
        
        metrics_data = [
            ['Metric', 'Value', 'Interpretation'],
            ['HHI Index', f"{concentration.get('herfindahl_index', 0)}", concentration.get('market_structure', 'Unknown')],
            ['CR4 Ratio', f"{concentration.get('concentration_ratio_cr4', 0)}%", 
             'High' if concentration.get('concentration_ratio_cr4', 0) > 40 else 'Moderate'],
            ['CR8 Ratio', f"{concentration.get('concentration_ratio_cr8', 0)}%",
             'High' if concentration.get('concentration_ratio_cr8', 0) > 60 else 'Moderate']
        ]
        
        metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.accent_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
        ]))
        
        elements.append(metrics_table)
        
        return elements
    
    def _create_top_performers(self, data, styles):
        """Create top performers section"""
        elements = []
        
        elements.append(Paragraph("Top Performers", styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        performers = data.get('top_performers', {})
        
        # Brands by SKUs
        elements.append(Paragraph("Top Brands by SKU Count", styles['CustomHeading2']))
        
        brands_skus = performers.get('brands_by_skus', [])[:10]
        if brands_skus:
            sku_data = [['Rank', 'Brand', 'SKU Count']]
            for idx, brand in enumerate(brands_skus, 1):
                sku_data.append([str(idx), brand['name'][:40], str(brand['sku_count'])])
            
            sku_table = Table(sku_data, colWidths=[0.7*inch, 3.5*inch, 1.3*inch])
            sku_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(sku_table)
        
        # Multi-country brands
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("International Brands (Multiple Countries)", styles['CustomHeading2']))
        
        multi_country = performers.get('brands_by_countries', [])[:10]
        if multi_country:
            country_data = [['Rank', 'Brand', 'Countries']]
            for idx, brand in enumerate(multi_country, 1):
                country_data.append([str(idx), brand['name'][:40], str(brand['country_count'])])
            
            country_table = Table(country_data, colWidths=[0.7*inch, 3.5*inch, 1.3*inch])
            country_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.light_gray, colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray)
            ]))
            
            elements.append(country_table)
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Add page numbers to each page"""
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.gray)
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawRightString(doc.pagesize[0] - 72, 30, text)
        canvas.restoreState()