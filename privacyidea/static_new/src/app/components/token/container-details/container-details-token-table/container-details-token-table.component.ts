import { NgClass } from "@angular/common";
import {
  Component,
  computed,
  ElementRef,
  inject,
  Input,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginator, MatPaginatorModule } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableDataSource,
  MatTableModule
} from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { SimpleConfirmationDialogComponent } from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";

@Component({
  selector: "app-container-details-token-table",
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatLabel,
    MatRow,
    MatTable,
    MatTableModule,
    MatIconButton,
    CopyButtonComponent,
    ReactiveFormsModule,
    FormsModule,
    MatPaginatorModule,
    NgClass,
    MatIconModule,
    MatTooltipModule,
    MatInput,
    ClearableInputComponent
  ],
  templateUrl: "./container-details-token-table.component.html",
  styleUrl: "./container-details-token-table.component.scss"
})
export class ContainerDetailsTokenTableComponent {
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly columnsKeyMap = this.tableUtilsService.pickColumns("serial", "tokentype", "active", "username");
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  displayedColumns: string[] = [...this.columnKeys, "actions"];
  pageSize = 5;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  pageIndex = this.tokenService.pageIndex;
  @Input() containerTokenData!: WritableSignal<MatTableDataSource<ContainerDetailToken, MatPaginator>>;

  filterValue: WritableSignal<string> = signal("");
  containerSerial = this.containerService.containerSerial;
  assignedUser: WritableSignal<{
    user_realm: string;
    user_name: string;
    user_resolver: string;
    user_id: string;
  }> = linkedSignal({
    source: () => this.containerService.containerDetail(),
    computation: (source) =>
      source.containers[0]?.users[0] ?? {
        user_realm: "",
        user_name: "",
        user_resolver: "",
        user_id: ""
      }
  });
  tokenSerial = this.tokenService.tokenSerial;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  apiFilter = this.tokenService.apiFilter;
  @ViewChild("filterInput", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  protected readonly sortedData = computed(() => {
    const source = this.containerTokenData();
    const data = source?.data ?? [];
    return this.tableUtilsService.clientsideSortTokenData([...data], this.sort());
  });

  dataSource = linkedSignal<ContainerDetailToken[], MatTableDataSource<ContainerDetailToken>>({
    source: () => this.sortedData(),
    computation: (newRows, previous) => {
      const ds = previous?.value ?? new MatTableDataSource<ContainerDetailToken>([]);
      ds.data = newRows;
      return ds;
    }
  });
  isAssignableToAllToken = computed<boolean>(() => {
    const assignedUser = this.assignedUser();
    if (assignedUser.user_name === "") {
      return false;
    }
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username === "");
  });

  isUnassignableFromAllToken = computed<boolean>(() => {
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username !== "");
  });

  ngAfterViewInit(): void {
    const ds = this.dataSource();
    ds.paginator = this.paginator;

    if (this.containerTokenData) {
      const externalDS = this.containerTokenData();
      externalDS.paginator = this.paginator;
      (externalDS as any)._sort = this.sort;
    }
    (ds as any)._sort = this.sort;

    ds.filterPredicate = (row: ContainerDetailToken, filter: string) => {
      const haystack = [row.serial, row.tokentype, row.username, String(row.active)].join(" ").toLowerCase();
      return haystack.includes(filter);
    };
  }

  handleFilterInput($event: Event): void {
    const raw = ($event.target as HTMLInputElement).value ?? "";
    const trimmed = raw.trim();
    this.filterValue.set(trimmed);
    const normalised = trimmed.toLowerCase();
    this.dataSource().filter = normalised;

    if (this.containerTokenData) {
      this.containerTokenData().filter = normalised;
    }
  }

  clearFilter(): void {
    this.filterValue.set("");
    this.dataSource().filter = "";

    if (this.containerTokenData) {
      this.containerTokenData().filter = "";
    }
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Remove Token",
          items: [tokenSerial],
          itemType: "token",
          confirmAction: { label: "Remove", value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.removeTokenFromContainer(containerSerial, tokenSerial).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              }
            });
          }
        }
      });
  }

  handleColumnClick(columnKey: string, token: ContainerDetailToken) {
    if (columnKey === "active") {
      this.toggleActive(token);
    }
  }

  toggleActive(token: ContainerDetailToken): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      }
    });
  }

  deleteAllTokens() {
    const serialList = this.containerTokenData().data.map((token) => token.serial);
    this.tokenService.bulkDeleteWithConfirmDialog(serialList, this.containerService.containerDetailResource.reload);
  }

  deleteTokenFromContainer(tokenSerial: string) {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Delete Token",
          items: [tokenSerial],
          itemType: "token",
          confirmAction: { label: "Delete", value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.deleteToken(tokenSerial).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              }
            });
          }
        }
      });
  }
}
