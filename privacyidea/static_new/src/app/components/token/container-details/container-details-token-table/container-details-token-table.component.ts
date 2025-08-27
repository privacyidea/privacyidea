import { NgClass } from "@angular/common";
import { Component, computed, effect, inject, Input, linkedSignal, ViewChild, WritableSignal } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortHeader, MatSortModule } from "@angular/material/sort";
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableDataSource,
  MatTableModule
} from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { UserAssignmentDialogComponent } from "../user-assignment-dialog/user-assignment-dialog.component";

const columnsKeyMap = [
  { key: "serial", label: "Serial" },
  { key: "tokentype", label: "Type" },
  { key: "active", label: "Active" },
  { key: "username", label: "User" }
];

@Component({
  selector: "app-container-details-token-table",
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatInput,
    MatLabel,
    MatPaginator,
    MatRow,
    MatSort,
    MatSortHeader,
    MatTable,
    NgClass,
    MatTableModule,
    MatSortModule,
    MatIcon,
    MatIconButton,
    MatButton,
    CopyButtonComponent,
    ReactiveFormsModule,
    FormsModule,
    MatTooltip
  ],
  templateUrl: "./container-details-token-table.component.html",
  styleUrl: "./container-details-token-table.component.scss"
})
export class ContainerDetailsTokenTableComponent {
  protected readonly dialog: MatDialog = inject(MatDialog);
  protected readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface =
    inject(TableUtilsService);
  protected readonly overflowService: OverflowServiceInterface =
    inject(OverflowService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  protected readonly columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = [
    ...columnsKeyMap.map((column) => column.key),
    "remove",
    "delete"
  ];
  pageSize = 10;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  filterValue = "";
  @Input() containerTokenData!: WritableSignal<
    MatTableDataSource<ContainerDetailToken, MatPaginator>
  >;
  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
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
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

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

  constructor() {
    effect(() => {
      if (!this.containerTokenData) {
        return;
      }
      this.dataSource.data = this.containerTokenData().data ?? [];
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;

    if (this.containerTokenData) {
      const externalDS = this.containerTokenData();
      externalDS.paginator = this.paginator;
      externalDS.sort = this.sort;
    }
  }

  handleFilterInput(event: Event): void {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    const normalised = this.filterValue.toLowerCase();

    this.dataSource.filter = normalised;
    if (this.containerTokenData) {
      this.containerTokenData().filter = normalised;
    }
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [tokenSerial],
          title: "Remove Token",
          type: "token",
          action: "remove",
          numberOfTokens: [tokenSerial].length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService
              .removeTokenFromContainer(containerSerial, tokenSerial)
              .subscribe({
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

  unassignFromAllToken() {
    const tokenToUnassign = this.containerTokenData().data.filter(
      (token) => token.username !== ""
    );
    if (tokenToUnassign.length === 0) {
      return;
    }
    const tokenSerials = tokenToUnassign.map((token) => token.serial);
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          type: "token",
          serial_list: tokenSerials,
          title: "Unassign User from All Tokens",
          action: "unassign",
          numberOfTokens: tokenSerials.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.unassignUserFromAll(tokenSerials).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              },
              error: (error) => {
                console.error("Error unassigning user from token:", error);
              }
            });
          }
        }
      });
  }

  assignToAllToken() {
    var username = this.assignedUser().user_name;
    var realm = this.assignedUser().user_realm;
    if (username === "" || realm === "") {
      this.dialog.open(ConfirmationDialogComponent, {
        data: {
          title: "No User Assigned",
          message: "Please assign a user to the container first."
        }
      });
      return;
    }

    var tokensToAssign = this.containerTokenData().data.filter((token) => {
      return token.username !== username;
    });
    if (tokensToAssign.length === 0) {
      return;
    }
    var tokensAssignedToOtherUser = tokensToAssign.filter(
      (token) => token.username !== ""
    );

    this.dialog
      .open<UserAssignmentDialogComponent, void, string | null>(UserAssignmentDialogComponent)
      .afterClosed()
      .subscribe((pin: string | null | undefined) => {
        if (pin == null) return;

        const tokenSerialsAssignedToOtherUser = tokensAssignedToOtherUser.map(token => token.serial);
        this.tokenService.unassignUserFromAll(tokenSerialsAssignedToOtherUser).subscribe({
          next: () => {
            const tokenSerialsToAssign = tokensToAssign.map(token => token.serial);
            this.tokenService.assignUserToAll({
              tokenSerials: tokenSerialsToAssign,
              username: username,
              realm: realm,
              pin: pin
            })
              .subscribe({
                next: () => this.containerService.containerDetailResource.reload(),
                error: (error) => console.error("Error assigning user to all tokens:", error)
              });
          },
          error: (error) => console.error("Error unassigning user from all tokens:", error)
        });
      });
  }

  toggleActive(token: ContainerDetailToken): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      }
    });
  }

  toggleAll(action: "activate" | "deactivate") {
    this.containerService.toggleAll(action).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      }
    });
  }

  removeAll() {
    const serial_list = this.containerTokenData()
      .data.map((token) => token.serial)
      .join(",");
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: serial_list.split(","),
          title: "Remove Token",
          type: "token",
          action: "remove",
          numberOfTokens: serial_list.split(",").length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.removeAll(this.containerSerial()).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              }
            });
          }
        }
      });
  }

  deleteAllTokens() {
    const serialList = this.containerTokenData()
      .data.map((token) => token.serial)
      .join(",");
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: serialList.split(","),
          title: "Delete All Tokens",
          type: "token",
          action: "delete",
          numberOfTokens: serialList.split(",").length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService
              .deleteAllTokens({
                containerSerial: this.containerSerial(),
                serialList: serialList
              })
              .subscribe({
                next: () => {
                  this.containerService.containerDetailResource.reload();
                }
              });
          }
        }
      });
  }

  deleteTokenFromContainer(tokenSerial: string) {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [tokenSerial],
          title: "Delete Token",
          type: "token",
          action: "delete",
          numberOfTokens: [tokenSerial].length
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
