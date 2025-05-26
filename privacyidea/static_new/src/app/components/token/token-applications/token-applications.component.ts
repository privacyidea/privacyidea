import { Component, linkedSignal, WritableSignal } from '@angular/core';
import { TokenApplicationsSshComponent } from './token-applications-ssh/token-applications-ssh.component';
import { TokenApplicationsOfflineComponent } from './token-applications-offline/token-applications-offline.component';
import { MatSelectModule } from '@angular/material/select';
import { MatTableDataSource } from '@angular/material/table';
import { MachineService } from '../../../services/machine/machine.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { TokenService } from '../../../services/token/token.service';
import { ContentService } from '../../../services/content/content.service';

@Component({
  selector: 'app-token-applications',
  standalone: true,
  imports: [
    TokenApplicationsSshComponent,
    TokenApplicationsOfflineComponent,
    MatSelectModule,
  ],
  templateUrl: './token-applications.component.html',
  styleUrls: ['./token-applications.component.scss'],
})
export class TokenApplicationsComponent {
  sshColumnsKeyMap = TokenApplicationsSshComponent.columnsKeyMap;
  offlineColumnsKeyMap = TokenApplicationsOfflineComponent.columnsKeyMap;
  tokenApplicationResource = this.machineService.tokenApplicationResource;
  selectedContent = this.contentService.selectedContent;
  tokenSerial = this.tokenService.tokenSerial;
  selectedApplicationType = this.machineService.selectedApplicationType;
  pageSize = this.machineService.pageSize;
  pageIndex = this.machineService.pageIndex;
  filterValue = this.machineService.filterValue;
  sort = this.machineService.sort;

  totalLength: WritableSignal<number> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource, previous) =>
      tokenApplicationResource?.result.value?.length ?? previous?.value ?? 0,
  });

  sshDataSource: WritableSignal<MatTableDataSource<any>> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource: any, previous) => {
      if (tokenApplicationResource) {
        const mappedData = tokenApplicationResource.result.value.map(
          (value: any) => ({
            serial: value.serial,
            service_id: value.options.service_id,
            user: value.options.user,
          }),
        );
        return new MatTableDataSource(mappedData);
      }
      return (
        previous?.value ??
        this.tableUtilsService.emptyDataSource(
          this.pageSize(),
          this.sshColumnsKeyMap,
        )
      );
    },
  });

  offlineDataSource: WritableSignal<MatTableDataSource<any>> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource: any, previous) => {
      if (tokenApplicationResource) {
        const mappedData = tokenApplicationResource.result.value.map(
          (value: any) => ({
            serial: value.serial,
            count: value.options.count,
            rounds: value.options.rounds,
          }),
        );
        return new MatTableDataSource(mappedData);
      }
      return (
        previous?.value ??
        this.tableUtilsService.emptyDataSource(
          this.pageSize(),
          this.offlineColumnsKeyMap,
        )
      );
    },
  });

  constructor(
    private machineService: MachineService,
    private tokenService: TokenService,
    private tableUtilsService: TableUtilsService,
    private contentService: ContentService,
  ) {}
}
