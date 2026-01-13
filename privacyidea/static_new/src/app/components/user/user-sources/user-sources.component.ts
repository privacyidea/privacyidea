import { Component, inject, linkedSignal, signal, viewChild, WritableSignal } from "@angular/core";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatPaginator, MatPaginatorModule } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { FormsModule } from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute, Router } from "@angular/router";
import { Resolver, ResolverService } from "../../../services/resolver/resolver.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { AuthService } from "../../../services/auth/auth.service";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ConfirmationDialogComponent } from "../../shared/confirmation-dialog/confirmation-dialog.component";

const columnKeysMap = [
  { key: "resolvername", label: "Name" },
  { key: "type", label: "Type" },
  { key: "actions", label: "Actions" }
];

@Component({
  selector: "app-user-sources",
  standalone: true,
  imports: [
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    ClearableInputComponent,
    ScrollToTopDirective
  ],
  templateUrl: "./user-sources.component.html",
  styleUrl: "./user-sources.component.scss"
})
export class UserSourcesComponent {
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);

  protected readonly resolverService = inject(ResolverService);
  protected readonly tableUtilsService = inject(TableUtilsService);
  protected readonly notificationService = inject(NotificationService);
  protected readonly dialog = inject(MatDialog);
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  paginator = viewChild(MatPaginator);
  sort = viewChild(MatSort);

  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  filterString = signal<string>("");

  resolversDataSource: WritableSignal<MatTableDataSource<Resolver>> = linkedSignal({
    source: () => ({
      resolvers: this.resolverService.resolvers(),
      paginator: this.paginator(),
      sort: this.sort()
    }),
    computation: (source) => {
      const dataSource = new MatTableDataSource(source.resolvers ?? []);
      dataSource.paginator = source.paginator ?? null;
      dataSource.sort = source.sort ?? null;

      dataSource.filterPredicate = (data: Resolver, filter: string) => {
        const normalizedFilter = filter.trim().toLowerCase();
        if (!normalizedFilter) {
          return true;
        }
        return (
          data.resolvername.toLowerCase().includes(normalizedFilter) ||
          data.type.toLowerCase().includes(normalizedFilter)
        );
      };

      dataSource.filter = this.filterString().trim().toLowerCase();
      return dataSource;
    }
  });

  onFilterInput(value: string): void {
    this.filterString.set(value);
    const ds = this.resolversDataSource();
    ds.filter = value.trim().toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.resolversDataSource();
    ds.filter = "";
  }

  onEditResolver(resolver: Resolver): void {
    this.router.navigate(["users/edit-resolver", resolver.resolvername]);
  }

  onDeleteResolver(resolver: Resolver): void {
    this.dialog.open(ConfirmationDialogComponent, {
      data: {
        serialList: [resolver.resolvername],
        title: $localize`Delete Resolver`,
        type: "resolver",
        action: "delete"
      }
    }).afterClosed().subscribe(result => {
      if (result) {
        this.resolverService.deleteResolver(resolver.resolvername).subscribe({
          next: () => {
            this.notificationService.openSnackBar($localize`Resolver "${resolver.resolvername}" deleted.`);
            this.resolverService.resolversResource.reload?.();
          },
          error: (err) => {
            const message = err.error?.result?.error?.message || err.message;
            this.notificationService.openSnackBar($localize`Failed to delete resolver. ${message}`);
          }
        });
      }
    });
  }
}