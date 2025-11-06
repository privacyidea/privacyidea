import { Component, effect, inject, linkedSignal, ViewChild, WritableSignal } from "@angular/core";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource
} from "@angular/material/table";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatSort, MatSortHeader } from "@angular/material/sort";
import { MatIconButton } from "@angular/material/button";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatPaginator } from "@angular/material/paginator";
import { MatTooltip } from "@angular/material/tooltip";
import { NgClass } from "@angular/common";
import { ContainerDetailToken } from "../../../../services/container/container.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserService, UserServiceInterface } from "../../../../services/user/user.service";

@Component({
  selector: "app-user-details-token-table",
  imports: [
    CopyButtonComponent,
    MatCell,
    MatCellDef,
    MatColumnDef,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatHeaderRowDef,
    MatIcon,
    MatIconButton,
    MatInput,
    MatLabel,
    MatPaginator,
    MatRow,
    MatRowDef,
    MatSort,
    MatSortHeader,
    MatTable,
    MatTooltip,
    NgClass,
    MatHeaderCellDef,
    MatNoDataRow
  ],
  templateUrl: "./user-details-token-table.component.html",
  styleUrl: "./user-details-token-table.component.scss"
})
export class UserDetailsTokenTableComponent {
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  readonly columnsKeyMap = this.tableUtilsService.pickColumns(
    "serial",
    "tokentype",
    "active",
    "description",
    "failcount",
    "maxfail",
    "container_serial"
  );
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  displayedColumns: string[] = [...this.columnsKeyMap.map((column) => column.key)];
  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
  filterValue = "";
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  userTokenData: WritableSignal<MatTableDataSource<any, MatPaginator>> = linkedSignal({
    source: this.tokenService.userTokenResource.value,
    computation: (userTokenResource, previous) => {
      if (!userTokenResource) {
        return previous?.value ?? new MatTableDataSource<any, MatPaginator>([]);
      }
      return new MatTableDataSource<any, MatPaginator>(userTokenResource.result?.value?.tokens ?? []);
    }
  });
  pageSize = 10;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  constructor() {
    effect(() => {
      if (!this.userTokenData) {
        return;
      }
      this.dataSource.data = this.userTokenData().data ?? [];
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }


  handleFilterInput($event: Event): void {
    this.filterValue = ($event.target as HTMLInputElement).value.trim();
    const normalised = this.filterValue.toLowerCase();
    this.dataSource.filter = normalised;
    if (this.userTokenData) {
      this.userTokenData().filter = normalised;
    }
  }

  toggleActive(token: ContainerDetailToken): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.tokenService.userTokenResource.reload();
      }
    });
  }

  resetFailCount(element: TokenDetails): void {
    if (!element.revoked && !element.locked && this.authService.actionAllowed("reset")) {
      this.tokenService.resetFailCount(element.serial).subscribe({
        next: () => {
          this.tokenService.userTokenResource.reload();
        }
      });
    }
  }
}
