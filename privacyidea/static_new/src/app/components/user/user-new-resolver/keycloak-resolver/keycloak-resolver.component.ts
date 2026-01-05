import { Component, signal } from "@angular/core";
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
import { AttributeMappingRow, HttpResolverComponent } from "../http-resolver/http-resolver.component";

@Component({
  selector: "app-keycloak-resolver",
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
  templateUrl: "../http-resolver/http-resolver.component.html",
  styleUrl: "../http-resolver/http-resolver.component.scss"
})
export class KeycloakResolverComponent extends HttpResolverComponent {
  override isAdvanced: boolean = true;

  override ngOnInit(): void {
    const data: any = this.data();

    if (!data.base_url) {
      data.base_url = "http://localhost:8080";
    }
    if (!data.timeout) {
      data.timeout = 60;
    }
    if (data.verify_tls === undefined) {
      data.verify_tls = true;
    }

    super.ngOnInit();
  }

  override defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "id" },
    { privacyideaAttr: "username", userStoreAttr: "userPrincipalName" },
    { privacyideaAttr: "email", userStoreAttr: "mail" },
    { privacyideaAttr: "givenname", userStoreAttr: "firstName" },
    { privacyideaAttr: "surname", userStoreAttr: "lastName" }
  ]);
}
