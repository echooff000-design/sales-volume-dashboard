elif "Trend" in query_type:
        is_deluxe = "Deluxe" in query_type
        is_sp = "Semi Premium" in query_type
        is_ms = "MS%" in query_type
        is_vol = "Volume" in query_type
        is_wod = "Unique Billed" in query_type
        
        deluxe_brands = ["IBDC", "N1WSUP", "OCBL", "GGSW", "Green Label", "IQ", "MCD Lux", "Mountain Oak"]
        sp_brands = ["MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", "GRR"]
        
        target_industry_name = "Deluxe-Whisky" if is_deluxe else "Semi Premium-Whisky"
        brand_list = deluxe_brands if is_deluxe else sp_brands
        industry_segs = ["Deluxe-Whisky", "Deluxe Plus-Whisky"] if is_deluxe else ["Semi Premium-Whisky"]
        
        # Map dynamic month labels to their respective dataframes explicitly
        trend_months = [tm_label, lm_label, m2_label, m3_label, m4_label, m5_label]
        months_dict = {
            tm_label: f_this,
            lm_label: f_last,
            m2_label: f_m2,
            m3_label: f_m3,
            m4_label: f_m4,
            m5_label: f_m5
        }
        
        html_trend = '<div class="table-wrapper"><table class="custom-dashboard-table">'
        html_trend += '<thead><tr><th class="seg-col-text">Brand</th>' + ''.join([f'<th>{m}</th>' for m in trend_months]) + '</tr></thead><tbody>'
        
        html_trend += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{target_industry_name}</b></td>'
        for m_key in trend_months:
            m_df = months_dict.get(m_key, pd.DataFrame())
            if m_df.empty:
                html_trend += '<td>-</td>'
                continue
            ind_sub = m_df[m_df["Segment"].isin(industry_segs)]
            if is_ms:
                ind_sum = ind_sub["Value"].sum()
                html_trend += '<td>100.0%</td>' if ind_sum > 0 else '<td>0.0%</td>'
            elif is_vol:
                html_trend += f'<td>{int(ind_sub["Value"].sum()):,}</td>'
            elif is_wod:
                html_trend += f'<td>{ind_sub[ind_sub["Value"] > 0]["LIC No"].nunique():,}</td>'
        html_trend += '</tr>'
        
        for b in brand_list:
            html_trend += f'<tr class="brand-row"><td class="brand-col-text">{b}</td>'
            for m_key in trend_months:
                m_df = months_dict.get(m_key, pd.DataFrame())
                if m_df.empty:
                    html_trend += '<td>-</td>'
                    continue
                ind_sub = m_df[m_df["Segment"].isin(industry_segs)]
                b_sub = ind_sub[ind_sub["Brand"] == b]
                
                if is_ms:
                    ind_tot = ind_sub["Value"].sum()
                    b_tot = b_sub["Value"].sum()
                    ms_pct = (b_tot / ind_tot * 100) if ind_tot > 0 else 0.0
                    html_trend += f'<td>{ms_pct:.1f}%</td>'
                elif is_vol:
                    html_trend += f'<td>{int(b_sub["Value"].sum()):,}</td>'
                elif is_wod:
                    html_trend += f'<td>{b_sub[b_sub["Value"] > 0]["LIC No"].nunique():,}</td>'
            html_trend += '</tr>'
            
        html_trend += '</tbody></table></div>'
        st.markdown(f"#### 📈 {query_type}:")
        render_zoomable_table(html_trend, "trend_query")
