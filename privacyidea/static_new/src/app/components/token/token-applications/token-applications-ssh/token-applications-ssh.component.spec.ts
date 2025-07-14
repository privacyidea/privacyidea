import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableDataSource } from '@angular/material/table';

import { TokenApplicationsSshComponent } from './token-applications-ssh.component';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import {
  MachineService,
  TokenApplication,
} from '../../../../services/machine/machine.service';
import { TokenService } from '../../../../services/token/token.service';
import { ContentService } from '../../../../services/content/content.service';
import {
  makeMachineServiceMock,
  tableUtilsMock,
} from '../../../../../testing/mock-services';
import { signal } from '@angular/core';

describe('TokenApplicationsSshComponent (Jest)', () => {
  let fixture: ComponentFixture<TokenApplicationsSshComponent>;
  let component: TokenApplicationsSshComponent;

  let mockTokenService: Partial<TokenService>;
  const mockContentService = {
    selectedContent: signal('token_applications'),
  };
  let mockKeywordFilterComponent: Partial<KeywordFilterComponent>;
  const machineServiceMock = makeMachineServiceMock();

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        TokenApplicationsSshComponent,
        MatTabsModule,
        KeywordFilterComponent,
        CopyButtonComponent,
      ],
      providers: [
        { provide: MachineService, useValue: machineServiceMock },
        { provide: TableUtilsService, useValue: tableUtilsMock },
        { provide: TokenService, useValue: mockTokenService },
        { provide: ContentService, useValue: mockContentService },
        {
          provide: KeywordFilterComponent,
          useValue: mockKeywordFilterComponent,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenApplicationsSshComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have correct displayedColumns', () => {
    expect(component.displayedColumns).toEqual([
      'serial',
      'service_id',
      'user',
    ]);
  });

  it('should return object strings correctly', () => {
    const options = { key1: 'value1', key2: 'value2' };
    expect(component.getObjectStrings(options)).toEqual([
      'key1: value1',
      'key2: value2',
    ]);
  });

  describe('dataSource computed', () => {
    it('returns a MatTableDataSource when tokenApplications() yields data', () => {
      const fakeApps: TokenApplication[] = [
        {
          id: 1,
          machine_id: 'm1',
          options: {},
          resolver: '',
          serial: '',
          type: '',
          application: '',
        },
      ];
      machineServiceMock.tokenApplications.set(fakeApps);

      // trigger recompute
      fixture.detectChanges();

      const ds = component.dataSource();
      expect(ds).toBeInstanceOf(MatTableDataSource);
      expect((ds as MatTableDataSource<TokenApplication>).data).toEqual(
        fakeApps,
      );
      expect(component.length()).toBe(1);
    });

    it('delegates to emptyDataSource when tokenApplications() is falsy', () => {
      machineServiceMock.tokenApplications.set(undefined);
      fixture.detectChanges();

      const ds = component.dataSource();
      expect(tableUtilsMock.emptyDataSource).toHaveBeenCalledWith(
        machineServiceMock.pageSize(),
        component.columnsKeyMap,
      );
      expect((ds as any).isEmpty).toBe(true);
      expect(component.length()).toBe(0);
    });
  });
});
