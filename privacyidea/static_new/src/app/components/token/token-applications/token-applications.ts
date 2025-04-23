import { Component, linkedSignal, WritableSignal } from '@angular/core';
import { TokenApplicationsSsh } from './token-applications-ssh/token-applications-ssh';
import { TokenApplicationsOffline } from './token-applications-offline/token-applications-offline';
import { MatSelectModule } from '@angular/material/select';
import { MatTableDataSource } from '@angular/material/table';
import { MachineService } from '../../../services/machine/machine.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { TokenService } from '../../../services/token/token.service';

@Component({
  selector: 'app-token-applications',
  standalone: true,
  imports: [TokenApplicationsSsh, TokenApplicationsOffline, MatSelectModule],
  templateUrl: './token-applications.html',
  styleUrls: ['./token-applications.scss'],
})
export class TokenApplications {
  sshColumnsKeyMap = TokenApplicationsSsh.columnsKeyMap;
  offlineColumnsKeyMap = TokenApplicationsOffline.columnsKeyMap;
  tokenApplicationResource = this.machineService.tokenApplicationResource;
  selectedContent = this.tokenService.selectedContent;
  tokenSerial = this.tokenService.tokenSerial;
  selectedApplicationType = this.machineService.selectedApplicationType;
  pageSize = this.machineService.pageSize;
  pageIndex = this.machineService.pageIndex;
  filterValue = this.machineService.filterValue;
  sort = this.machineService.sort;

  totalLength: WritableSignal<number> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource, previous) => {
      if (tokenApplicationResource) {
        return tokenApplicationResource.result.value.length;
      }
      return previous?.value ?? 0;
    },
  });

  sshDataSource: WritableSignal<MatTableDataSource<any>> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource: any, previous) => {
      if (tokenApplicationResource) {
        const mappedData = tokenApplicationResource.result.value.map(
          (value: any) => ({
            serial: value.serial,
            serviceid: value.options.service_id,
            ssh_user: value.options.user,
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
  ) {}
}
