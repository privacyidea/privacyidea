# -*- coding: utf-8 -*-

    <ul>
    % for tok in c.tokenArray:
        %if tok['privacyIDEA.Isactive']:
        <li><a class='activeToken' href='' 
        	onclick="selectToken('${tok['privacyIDEA.TokenSerialnumber']}'); return false;">
        		${tok['privacyIDEA.TokenSerialnumber']}
        </a></li>      
        %else:
        <li><a class='disabledToken' href='' 
        	onclick="selectToken('${tok['privacyIDEA.TokenSerialnumber']}'); return false;"> 
        		${tok['privacyIDEA.TokenSerialnumber']} </a></li>
        %endif        
    % endfor
    </ul>
