import { Component } from '@angular/core';
import { HttpResolverComponent } from "../http-resolver/http-resolver.component";
import { FormsModule } from "@angular/forms";
import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTableModule } from "@angular/material/table";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatDivider } from "@angular/material/list";

@Component({
  selector: 'app-entraid-resolver',
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatSlideToggle,
    MatHint,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatDivider
  ],
  templateUrl: '../http-resolver/http-resolver.component.html',
  styleUrl: '../http-resolver/http-resolver.component.scss'
})
export class EntraidResolverComponent extends HttpResolverComponent {
  override isAdvanced: boolean = true;

  override ngOnInit(): void {
    const data: any = this.data ?? {};

      data.url = "https://graph.microsoft.com/v1.0";
      data.timeout = 60;
      data.attribute_mapping = {
        userid: "id",
        username: "userPrincipalName",
        email: "mail",
        givenname: "givenName",
        mobile: "mobilePhone",
        phone: "businessPhones",
        surname: "surname"
      } as Record<string, string>;
      data.tls_verify = true;

    this.data = data;
    super.ngOnInit();
  }
}
