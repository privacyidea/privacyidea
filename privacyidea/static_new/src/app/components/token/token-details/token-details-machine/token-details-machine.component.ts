import { NgClass } from "@angular/common";
import { Component, computed, inject, Input, linkedSignal, signal, Signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatList, MatListItem } from "@angular/material/list";
import { MatCell, MatColumnDef, MatRow, MatTableModule } from "@angular/material/table";
import { Observable, switchMap } from "rxjs";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { EditableElement, EditButtonsComponent } from "../../../shared/edit-buttons/edit-buttons.component";
import {
  MachineService,
  MachineServiceInterface,
  TokenApplication,
  TokenApplications
} from "../../../../services/machine/machine.service";
import { CdkTableDataSourceInput, DataSource } from "@angular/cdk/table";
import { Data } from "@angular/router";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";

@Component({
  selector: "app-token-details-machine",
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatCell,
    MatList,
    MatListItem,
    FormsModule,
    MatIconButton,
    MatIcon,
    MatDivider,
    MatRow,
    NgClass
  ],
  templateUrl: "./token-details-machine.component.html",
  styleUrl: "./token-details-machine.component.scss"
})
export class TokenDetailsMachineComponent {
  protected readonly JSON = JSON;
  protected readonly Object = Object;
  private machineService: MachineServiceInterface = inject(MachineService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected isEditing: WritableSignal<boolean> = signal(false);

  machineData = computed<TokenApplications>(() => this.machineService.tokenApplications() || []);

  unassignMachine(mtid: number, application: "ssh" | "offline"): void {
    this.machineService
      .deleteAssignMachineToToken({
        serial: this.contentService.tokenSerial(),
        application: application,
        mtid: mtid.toString()
      })
      .subscribe({
        next: () => {
          this.machineService.tokenApplicationResource.reload();
        }
      });
  }

  dataSourceFromMachine(machine: TokenApplication): CdkTableDataSourceInput<any> {
    return new Array(machine);
  }
}
