import { NgClass } from "@angular/common";
import { Component } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { MatCell, MatColumnDef, MatRow, MatTable, MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { EditButtonsComponent } from "../../shared/edit-buttons/edit-buttons.component";
import { TokenDetailsActionsComponent } from "./token-details-actions/token-details-actions.component";
import { TokenDetailsInfoComponent } from "./token-details-info/token-details-info.component";
import { TokenDetailsUserSelfServiceComponent } from "./token-details-user/token-details-user.self-service.component";
import { TokenDetailsComponent } from "./token-details.component";

@Component({
  selector: "app-token-details-self-service",
  standalone: true,
  imports: [
    MatCell,
    MatTableModule,
    MatColumnDef,
    MatIcon,
    MatListItem,
    MatRow,
    MatTable,
    NgClass,
    FormsModule,
    MatInput,
    MatFormFieldModule,
    MatSelectModule,
    ReactiveFormsModule,
    MatIconButton,
    TokenDetailsUserSelfServiceComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    EditButtonsComponent,
    CopyButtonComponent,
    ClearableInputComponent
  ],
  templateUrl: "./token-details.self-service.component.html",
  styleUrls: ["./token-details.component.scss"]
})
export class TokenDetailsSelfServiceComponent extends TokenDetailsComponent {
  toggleActive(active: boolean): void {
    this.tokenService.toggleActive(this.tokenSerial(), active).subscribe(() => {
      this.tokenService.tokenDetailResource.reload();
    });
  }
}
