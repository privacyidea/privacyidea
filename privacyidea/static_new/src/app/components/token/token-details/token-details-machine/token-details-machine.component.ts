import { NgClass } from "@angular/common";
import { Component, computed, inject, input, Input, linkedSignal, signal, Signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { MatList, MatListItem } from "@angular/material/list";
import { MatCell, MatColumnDef, MatRow, MatTableModule } from "@angular/material/table";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import {
  MachineService,
  MachineServiceInterface,
  TokenApplication,
  TokenApplications
} from "../../../../services/machine/machine.service";
import { CdkTableDataSourceInput } from "@angular/cdk/table";
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
  private contentService: ContentServiceInterface = inject(ContentService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);

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
