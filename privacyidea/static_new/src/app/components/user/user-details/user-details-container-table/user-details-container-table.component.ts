import { Component, effect, inject, linkedSignal, ViewChild, WritableSignal } from "@angular/core";
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
import { MatPaginator } from "@angular/material/paginator";
import { MatSort } from "@angular/material/sort";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import {
  ContainerDetailData,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { UserService, UserServiceInterface } from "../../../../services/user/user.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { MatTooltip } from "@angular/material/tooltip";

const columnsKeyMap = [
  { key: "serial", label: "Serial" },
  { key: "type", label: "Type" },
  { key: "states", label: "Status" },
  { key: "description", label: "Description" },
  { key: "realms", label: "Container Realms" }
];

@Component({
  selector: "app-user-details-container-table",
  imports: [
    CopyButtonComponent,
    ClearableInputComponent,
    MatHeaderRowDef,
    MatRowDef,
    MatNoDataRow,
    MatFormField,
    MatLabel,
    MatInput,
    MatPaginator,
    MatTable,
    MatSort,
    MatHeaderCellDef,
    MatColumnDef,
    MatHeaderCell,
    MatCellDef,
    MatCell,
    NgClass,
    MatTooltip,
    MatHeaderRow,
    MatRow,
    MatFormField,
    MatLabel
  ],
  templateUrl: "./user-details-container-table.component.html",
  styleUrl: "./user-details-container-table.component.scss"
})
export class UserDetailsContainerTableComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly userService: UserServiceInterface = inject(UserService);

  readonly columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = columnsKeyMap.map(c => c.key);

  dataSource = new MatTableDataSource<ContainerDetailData>([]);
  filterValue = "";

  pageSize = 10;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  userContainers: WritableSignal<ContainerDetailData[]> = linkedSignal({
    source: this.containerService.containerResource.value,
    computation: (containerResource, previous) => {
      const username = this.userService.detailsUsername();
      const realm = this.userService.selectedUserRealm();

      if (!containerResource?.result?.value) {
        return previous?.value ?? [];
      }

      const all = containerResource.result.value.containers ?? [];
      const filtered = all.filter((c: ContainerDetailData) =>
        (c.users ?? []).some(u => u.user_name === username && u.user_realm === realm)
      );

      return filtered;
    }
  });

  constructor() {
    effect(() => {
      this.dataSource.data = this.userContainers();
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;

    this.dataSource.filterPredicate = (row: ContainerDetailData, filter: string) => {
      const currentState = (row.states?.[0] ?? "").toString();
      const realmsJoined = (row.realms ?? []).join(" ");
      const haystack = [
        row.serial,
        row.type,
        row.description ?? "",
        currentState,
        realmsJoined
      ].join(" ").toLowerCase();

      return haystack.includes(filter);
    };
  }

  handleFilterInput($event: Event): void {
    this.filterValue = ($event.target as HTMLInputElement).value.trim().toLowerCase();
    this.dataSource.filter = this.filterValue;
  }

  onPageSizeChange(size: number) {
    this.pageSize = size;
  }

  handleStateClick(element: ContainerDetailData) {
    this.containerService.toggleActive(element.serial, element.states).subscribe({
      next: () => this.containerService.containerResource.reload()
    });
  }
}
